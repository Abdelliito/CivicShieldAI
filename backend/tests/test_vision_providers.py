"""Adapter protocol/validation tests use HTTP mocks, never live-provider claims."""
import base64
import hashlib
import json
import importlib.util
from pathlib import Path

import httpx
import pytest
from PIL import Image

from app import intelligence as ai
from app import vision


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    for name in tuple(vision.os.environ):
        if name.startswith(('VISION_', 'OPENAI_', 'GEMINI_', 'GOOGLE_API_', 'ANTHROPIC_', 'COMPATIBLE_', 'OLLAMA_', 'HF_')):
            monkeypatch.delenv(name, raising=False)


@pytest.fixture
def photograph(tmp_path):
    image = tmp_path / 'civic.png'
    Image.new('RGB', (24, 24), '#56685b').save(image)
    return image


def analysis(**changes):
    return {**ai.classify_text('Blocked drain beside a road').model_dump(),
            'summary': 'The photograph shows a drainage opening partly obstructed by visible debris; human review is needed.',
            'evidence': ['Visible debris covers part of a drainage opening.'],
            'uncertainty': ['Depth and underground drainage condition cannot be established from this photograph.'],
            'image_analyzed': True, 'method': 'vision_model', 'relevance': 'relevant', 'detected_title': 'Blocked drainage opening', **changes}


def response(provider, output):
    text = json.dumps(output)
    return {
        'openai': {'status': 'completed', 'output': [{'content': [{'type': 'output_text', 'text': text}]}]},
        'gemini': {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': text}]}}]},
        'anthropic': {'stop_reason': 'end_turn', 'content': [{'type': 'text', 'text': text}]},
        'ollama': {'done': True, 'done_reason': 'stop', 'response': text},
    }.get(provider, {'choices': [{'finish_reason': 'stop', 'message': {'content': text}}]})


@pytest.mark.parametrize('provider', vision.PROVIDERS)
def test_distinct_authenticated_image_protocols(provider, photograph, monkeypatch):
    monkeypatch.setenv('VISION_PROVIDER', provider)
    monkeypatch.setenv('VISION_MODEL', 'vision-model-for-protocol-test')
    monkeypatch.setenv('VISION_API_KEY', 'protocol-test-secret')
    if provider == 'openai_compatible':
        monkeypatch.setenv('VISION_ENDPOINT', 'https://vision.example.test/v1/chat/completions')
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=response(provider, analysis()))
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = vision.analyze_image_file(photograph, client=client)
    assert result['status'] == 'success' and result['image_analyzed'] and result['attempts'] == 1
    assert result['provider'] == provider and result['source_sha256'] == hashlib.sha256(photograph.read_bytes()).hexdigest()
    request = requests[0]
    payload = json.loads(request.content)
    if provider == 'gemini':
        assert request.headers['x-goog-api-key'] == 'protocol-test-secret'
        assert request.url.path.endswith('/vision-model-for-protocol-test:generateContent')
        encoded = payload['contents'][0]['parts'][0]['inline_data']['data']
        assert payload['contents'][0]['parts'][0]['inline_data']['mime_type'] == 'image/png'
        assert 'Authorization' not in request.headers and 'key' not in request.url.params
    elif provider == 'anthropic':
        assert request.headers['x-api-key'] == 'protocol-test-secret'
        assert request.headers['anthropic-version'] == '2023-06-01'
        encoded = payload['messages'][0]['content'][0]['source']['data']
        assert 'Authorization' not in request.headers
    elif provider == 'ollama':
        assert payload['stream'] is False and isinstance(payload['format'], dict)
        encoded = payload['images'][0]
    elif provider == 'openai':
        assert payload['store'] is False and payload['text']['format']['type'] == 'json_schema'
        encoded = payload['input'][0]['content'][1]['image_url'].split(',', 1)[1]
    else:
        encoded = payload['messages'][1]['content'][1]['image_url']['url'].split(',', 1)[1]
    assert base64.b64decode(encoded) == photograph.read_bytes()
    assert 'tools' not in payload


def test_no_key_is_actionable_and_never_calls_provider(photograph, monkeypatch):
    monkeypatch.setattr(vision.httpx, 'post', lambda *a, **k: pytest.fail('No key must not send the image'))
    result = vision.analyze_image_file(photograph)
    assert result['status'] == 'unconfigured' and not result['image_analyzed']
    assert result['can_submit'] and result['attempts'] == 0
    assert result['errors'][0]['code'] == 'missing_key'
    assert result['category'] == 'Other civic infrastructure hazards'


@pytest.mark.parametrize(('status', 'error', 'expected'), [
    (401, {}, 'authentication'), (403, {}, 'authentication'),
    (429, {'code': 'insufficient_quota'}, 'quota'), (429, {}, 'rate_limit'),
    (404, {}, 'model_or_endpoint'), (400, {}, 'unsupported_request'),
    (500, {}, 'provider_unavailable'), (302, {}, 'redirect_rejected'),
])
def test_error_codes_are_specific_sanitized_and_not_success(status, error, expected, photograph, monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'secret-never-display')
    response_body = {'error': {**error, 'message': 'secret-never-display image-data private record'}}
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(status, json=response_body, headers={'Location': 'https://attacker.example'}))) as client:
        result = vision.analyze_image_file(photograph, client=client)
    assert result['status'] == 'failed' and result['image_analyzed'] is False
    assert result['errors'][0]['code'] == expected
    assert 'secret-never-display' not in json.dumps(result) and 'private record' not in json.dumps(result)


@pytest.mark.parametrize('exception,expected', [(httpx.ConnectError('secret endpoint'), 'connection'), (httpx.ReadTimeout('secret request'), 'timeout')])
def test_network_errors_are_safe(exception, expected, photograph, monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'secret')
    def handler(request):
        raise exception
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = vision.analyze_image_file(photograph, client=client)
    assert result['errors'][0]['code'] == expected and not result['image_analyzed']
    assert 'secret' not in json.dumps(result)


def test_configured_fallback_receives_only_its_own_credentials(photograph, monkeypatch):
    monkeypatch.setenv('VISION_API_KEY', 'primary-secret')
    monkeypatch.setenv('VISION_FALLBACK_PROVIDER', 'gemini')
    monkeypatch.setenv('GEMINI_API_KEY', 'fallback-secret')
    monkeypatch.setenv('GEMINI_MODEL', 'gemini-vision-test')
    calls = []
    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, json={'error': {'code': 'insufficient_quota'}})
        assert request.headers['x-goog-api-key'] == 'fallback-secret'
        assert 'primary-secret' not in str(request.headers)
        return httpx.Response(200, json=response('gemini', analysis()))
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = vision.analyze_image_file(photograph, client=client)
    assert result['image_analyzed'] and result['provider'] == 'gemini' and result['attempts'] == 2
    assert result['errors'][0]['code'] == 'quota'


def test_missing_fallback_key_never_reuses_primary_secret(photograph, monkeypatch):
    monkeypatch.setenv('VISION_API_KEY', 'primary-secret')
    monkeypatch.setenv('VISION_FALLBACK_PROVIDER', 'gemini')
    monkeypatch.setenv('GEMINI_MODEL', 'gemini-vision-test')
    calls = []
    with httpx.Client(transport=httpx.MockTransport(lambda request: calls.append(request) or httpx.Response(500))) as client:
        result = vision.analyze_image_file(photograph, client=client)
    assert len(calls) == 1 and result['errors'][-1]['code'] == 'missing_key'


@pytest.mark.parametrize('changes', [{'image_analyzed': False, 'method': 'deterministic_text'}, {'category': 'Earthquake'}, {'assign_team_id': 4}, {'evidence': []}, {'confidence': .9}, {'recommended_department': 'Fake Department'}])
def test_invalid_or_false_provider_results_never_show_detection(changes, photograph, monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'secret')
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=response('openai', analysis(**changes))))) as client:
        result = vision.analyze_image_file(photograph, client=client)
    assert result['status'] == 'failed' and not result['image_analyzed']


@pytest.mark.parametrize('relevance', ['irrelevant', 'uncertain'])
def test_irrelevant_or_ambiguous_photo_cannot_claim_civic_detection(relevance, photograph, monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'secret')
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=response('openai', analysis(relevance=relevance))))) as client:
        result = vision.analyze_image_file(photograph, description='Huge pothole by school', client=client)
    assert result['image_analyzed'] is True and result['status'] == relevance
    assert result['category'] == 'Other civic infrastructure hazards' and result['severity'] == 'Low'


@pytest.mark.parametrize('provider,bad_body', [
    ('openai', {'status': 'incomplete', 'output': []}),
    ('gemini', {'candidates': [{'finishReason': 'MAX_TOKENS'}]}),
    ('anthropic', {'stop_reason': 'max_tokens', 'content': []}),
    ('ollama', {'done': False, 'response': '{}'}),
    ('huggingface', {'choices': [{'finish_reason': 'length', 'message': {'content': '{}'}}]}),
])
def test_truncated_or_refused_responses_are_not_success(provider, bad_body, photograph, monkeypatch):
    monkeypatch.setenv('VISION_PROVIDER', provider)
    monkeypatch.setenv('VISION_MODEL', 'vision-test')
    monkeypatch.setenv('VISION_API_KEY', 'secret')
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=bad_body))) as client:
        result = vision.analyze_image_file(photograph, client=client)
    assert not result['image_analyzed'] and result['status'] == 'failed'


def test_invalid_image_is_rejected_before_external_request(tmp_path, monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'secret')
    invalid = tmp_path / 'invalid.jpg'
    invalid.write_bytes(b'not an image')
    monkeypatch.setattr(vision.httpx, 'post', lambda *a, **k: pytest.fail('Invalid file must never leave backend'))
    result = vision.analyze_image_file(invalid)
    assert result['status'] == 'invalid_image' and not result['can_submit'] and not result['image_analyzed']


def test_key_aliases_models_and_safe_status(monkeypatch):
    monkeypatch.setenv('VISION_PROVIDER', 'google')
    monkeypatch.setenv('GOOGLE_API_KEY', 'no-secret-in-status')
    monkeypatch.setenv('GEMINI_MODEL', 'explicit-selected-vision-model')
    status = vision.provider_status()
    assert status['configured'] and status['providers'][0]['provider'] == 'gemini'
    assert status['providers'][0]['model'] == 'explicit-selected-vision-model'
    assert 'no-secret-in-status' not in json.dumps(status)
    assert status['verified_live'] is False


def test_legacy_openai_configuration_and_model_precedence(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'secret')
    monkeypatch.setenv('OPENAI_MODEL', 'retain-exact-user-model')
    assert vision.configurations()[0].model == 'retain-exact-user-model'
    monkeypatch.setenv('VISION_MODEL', 'explicit-generic-model')
    assert vision.configurations()[0].model == 'explicit-generic-model'


def test_project_root_dotenv_with_bom_loads_and_shell_wins(tmp_path, monkeypatch):
    from app import config
    # Track both names so dotenv's direct os.environ writes cannot leak into
    # subsequent tests after monkeypatch restores this fixture's environment.
    for name in ('OPENAI_API_KEY', 'OPENAI_MODEL'):
        monkeypatch.setenv(name, '')
        monkeypatch.delenv(name)
    nested = tmp_path / 'backend' / 'app'
    nested.mkdir(parents=True)
    copied = nested / 'config.py'
    copied.write_text(Path(config.__file__).read_text(encoding='utf-8'), encoding='utf-8')
    (tmp_path / '.env').write_text('OPENAI_API_KEY=file-only-test-key\nOPENAI_MODEL=file-model\n', encoding='utf-8-sig')
    spec = importlib.util.spec_from_file_location('vision_config_test', copied)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    assert loaded.settings.openai_api_key == 'file-only-test-key'
    assert loaded.settings.openai_model == 'file-model'
    monkeypatch.setenv('OPENAI_API_KEY', 'shell-only-test-key')
    spec.loader.exec_module(loaded)
    assert loaded.settings.openai_api_key == 'shell-only-test-key'


def test_insecure_or_credential_embedded_endpoints_do_not_send_keys(photograph, monkeypatch):
    monkeypatch.setenv('VISION_API_KEY', 'secret')
    monkeypatch.setattr(vision.httpx, 'post', lambda *a, **k: pytest.fail('Invalid endpoint must never receive a key'))
    for endpoint in ['http://public.example/v1/responses', 'https://user:password@example.test/api', 'https://example.test/api?key=secret']:
        monkeypatch.setenv('VISION_ENDPOINT', endpoint)
        result = vision.analyze_image_file(photograph)
        assert result['attempts'] == 0 and not result['image_analyzed']
        assert 'password' not in json.dumps(vision.provider_status())


def test_failure_preview_reused_only_for_same_photo_and_configuration(photograph, monkeypatch):
    payload = vision.analyze_image_file(photograph)
    assert vision.reusable_analysis(payload, photograph) == payload
    monkeypatch.setenv('OPENAI_API_KEY', 'new-secret')
    assert vision.reusable_analysis(payload, photograph) is None
    monkeypatch.delenv('OPENAI_API_KEY')
    photograph.write_bytes(b'changed')
    assert vision.reusable_analysis(payload, photograph) is None
