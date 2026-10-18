import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Camera, CheckCircle2, LocateFixed, UploadCloud, X, MapPin, TriangleAlert, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { api, json, upload, useAction } from "../lib/api";
import type { Incident, Json } from "../lib/types";
import { CATEGORIES } from "../lib/types";
import { Button, Evidence, Field, Modal } from "./UI";
import { CivicMap } from "./Map";

type PhotoState = "idle" | "uploading" | "analyzing" | "done" | "error";
export function ReportForm({ open, onClose, incident, onSaved, initialPhotoMode }: {
  open: boolean; onClose: () => void; incident?: Incident; onSaved?: (id: number) => void; initialPhotoMode?: "upload" | "camera";
}) {
  const photoInput = useRef<HTMLInputElement>(null), cameraInput = useRef<HTMLInputElement>(null);
  const photoGeneration = useRef(0), autoLocationStarted = useRef(false), mounted = useRef(true);
  const suggestions = useRef<{ title?: string; category?: string }>({});
  const pickerOpened = useRef(false);
  const [title, setTitle] = useState(incident?.title || ""),
    [description, setDescription] = useState(incident?.description || ""),
    [category, setCategory] = useState(incident?.category || ""),
    [location, setLocation] = useState(incident?.location_name || ""),
    [latitude, setLatitude] = useState(incident ? String(incident.latitude) : ""),
    [longitude, setLongitude] = useState(incident ? String(incident.longitude) : ""),
    [mapPosition, setMapPosition] = useState({ latitude: incident?.latitude ?? 31.5204, longitude: incident?.longitude ?? 74.3587 }),
    [file, setFile] = useState<File | null>(null), [preview, setPreview] = useState(""),
    [attachmentId, setAttachmentId] = useState<number | null>(null),
    [photoState, setPhotoState] = useState<PhotoState>("idle"),
    [analysis, setAnalysis] = useState<Json | null>(null), [photoError, setPhotoError] = useState(""),
    [detectionSucceeded, setDetectionSucceeded] = useState(false),
    [gps, setGps] = useState(false), [locationMessage, setLocationMessage] = useState(incident ? "Saved report location. Move the marker if needed." : "Finding your location…"),
    [locationConfirmed, setLocationConfirmed] = useState(Boolean(incident));
  const photoBusy = photoState === "uploading" || photoState === "analyzing";
  const action = useAction(async () => {
    const lat = Number(latitude), lng = Number(longitude);
    if (!locationConfirmed || !latitude.trim() || !longitude.trim() || !Number.isFinite(lat) || !Number.isFinite(lng) || Math.abs(lat) > 90 || Math.abs(lng) > 180)
      throw new Error("Choose the problem’s location on the map, use your location, or enter valid coordinates.");
    if (file && !attachmentId) throw new Error("The photo has not uploaded. Try again or remove it to write a report instead.");
    if (analysis?.can_submit === false) throw new Error("Choose a supported, readable photograph before submitting.");
    if (!file && !incident?.attachments?.some((a) => a.kind !== "completion") && !title.trim() && !description.trim())
      throw new Error("Add a photograph or write a short description of the problem.");
    const attachmentIds = incident?.attachments?.filter((a) => a.kind !== "completion").map((a) => a.id) || [];
    if (attachmentId && !attachmentIds.includes(attachmentId)) attachmentIds.push(attachmentId);
    const result = await api<Incident>(incident ? `/reports/${incident.id}` : "/reports", {
      method: incident ? "PATCH" : "POST",
      body: json({ title: title.trim(), description: description.trim(), category: category || undefined,
        location_name: location.trim(), latitude: lat, longitude: lng, attachment_ids: attachmentIds }),
    });
    onSaved?.(result.id); onClose(); return result;
  }, incident ? "Report updated" : "Report sent. Your authority will review it.");
  const remove = useAction((id: number) => api(`/uploads/${id}`, { method: "DELETE" }), "Photo removed");
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    if (!incident && !autoLocationStarted.current) { autoLocationStarted.current = true; locate(); }
  }, [incident]);
  function bindInitialPicker(node: HTMLInputElement | null, mode: "upload" | "camera") {
    (mode === "camera" ? cameraInput : photoInput).current = node;
    // Radix mounts portal contents after the form's first effect. Open only
    // once the actual input exists, while the initiating click is still active.
    if (node && initialPhotoMode === mode && !pickerOpened.current) {
      pickerOpened.current = true;
      node.click();
    }
  }
  function setPoint(lat: number, lng: number) {
    setLatitude(String(Number(lat.toFixed(6)))); setLongitude(String(Number(lng.toFixed(6))));
    setMapPosition({ latitude: lat, longitude: lng }); setLocationConfirmed(true);
    setLocationMessage("Location selected. Check that the marker is where the problem is.");
  }
  function updateCoordinate(axis: "latitude" | "longitude", value: string) {
    if (axis === "latitude") setLatitude(value); else setLongitude(value);
    const coordinate = Number(value), limit = axis === "latitude" ? 90 : 180;
    setLocationConfirmed(Boolean(value.trim()) && Number.isFinite(coordinate) && Math.abs(coordinate) <= limit);
    if (value.trim() && Number.isFinite(coordinate) && Math.abs(coordinate) <= limit)
      setMapPosition((current) => ({ ...current, [axis]: coordinate }));
  }
  async function analyzePhoto(next: File, generation: number, uploadedId?: number) {
    setPhotoError(""); setAnalysis(null); setDetectionSucceeded(false); setPhotoState(uploadedId ? "analyzing" : "uploading");
    try {
      const id = uploadedId ?? (await upload(next)).id;
      if (!mounted.current || generation !== photoGeneration.current) {
        if (!uploadedId) void api(`/uploads/${id}`, { method: "DELETE" }).catch(() => {});
        return;
      }
      setAttachmentId(id); setPhotoState("analyzing");
      const result = await api<{ attachment_id: number; analysis: Json; detection_succeeded: boolean }>(`/uploads/${id}/analyze`, {
        method: "POST", body: json({ title, description }),
      });
      if (!mounted.current || generation !== photoGeneration.current) return;
      const finding = result.analysis || {};
      setAnalysis(finding); setPhotoState("done");
      setDetectionSucceeded(result.detection_succeeded === true && finding.image_analyzed === true);
      if (result.detection_succeeded && finding.image_analyzed === true) {
        const previous = suggestions.current;
        suggestions.current = { title: finding.detected_title, category: finding.category };
        if (finding.detected_title) setTitle((current) => !current || current === previous.title ? finding.detected_title : current);
        if (CATEGORIES.includes(finding.category)) setCategory((current) => !current || current === previous.category ? finding.category : current);
      }
    } catch (error) {
      if (!mounted.current || generation !== photoGeneration.current) return;
      setPhotoState("error"); setPhotoError(error instanceof Error ? error.message : "We could not analyze this photograph.");
    }
  }
  function changeFile(next: File | null) {
    if (next && !["image/jpeg", "image/png", "image/webp"].includes(next.type)) return toast.error("Choose a JPG, PNG or WebP photograph.");
    if (next && next.size > 8 * 1024 * 1024) return toast.error("Images must be smaller than 8 MB.");
    const generation = ++photoGeneration.current;
    const previousSuggestions = suggestions.current;
    setTitle((current) => current === previousSuggestions.title ? "" : current);
    setCategory((current) => current === previousSuggestions.category ? "" : current);
    suggestions.current = {};
    if (attachmentId) void api(`/uploads/${attachmentId}`, { method: "DELETE" }).catch(() => {});
    setAttachmentId(null); setAnalysis(null); setDetectionSucceeded(false); setPhotoError(""); setPhotoState("idle");
    setFile(next); setPreview(next ? URL.createObjectURL(next) : "");
    if (!next && photoInput.current) photoInput.current.value = "";
    if (!next && cameraInput.current) cameraInput.current.value = "";
    if (next) void analyzePhoto(next, generation);
  }
  function locate() {
    if (!navigator.geolocation) { setLocationMessage("Location is unavailable. Tap the map or enter coordinates below."); return; }
    setGps(true); setLocationMessage("Finding your location…");
    navigator.geolocation.getCurrentPosition((position) => {
      if (!mounted.current) return;
      setPoint(position.coords.latitude, position.coords.longitude); setGps(false);
    }, () => {
      if (!mounted.current) return;
      setGps(false); setLocationMessage("Location permission is unavailable. Tap the map to select the problem’s location.");
    }, { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 });
  }
  function submit(event: FormEvent) { event.preventDefault(); action.mutate(undefined); }
  const imageExamined = analysis?.image_analyzed === true;
  const detected = detectionSucceeded && imageExamined && analysis?.status === "success";
  return <Modal open={open} onClose={onClose} title={incident ? "Edit your report" : "Report a problem"}
    description="Add a photo, check the location, and send. A person will review your report." wide>
    <form onSubmit={submit} className="report-form photo-first-form">
      <section className="photo-report-section">
        <div className="report-step-heading"><span>01</span><div><h3>Add a photo of the problem</h3><p>Take a photo from a safe distance. We’ll try to identify the issue.</p></div></div>
        <div className={`photo-first-picker ${preview ? "has-photo" : ""}`}>
          {preview ? <div className="selected-image"><img src={preview} alt="Selected hazard preview" /><button type="button" aria-label="Remove selected photograph" className="icon-button" onClick={() => changeFile(null)}><X size={18} /></button></div> :
            <label className="upload-zone"><UploadCloud size={29} /><strong>Choose a photograph</strong><span>JPG, PNG, WebP · up to 8 MB</span><input ref={(node) => bindInitialPicker(node, "upload")} aria-label="Hazard photograph" type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => changeFile(e.target.files?.[0] || null)} /></label>}
          <div className="photo-picker-actions"><Button type="button" className="button-secondary" onClick={() => cameraInput.current?.click()}><Camera size={17} />Take photo</Button>{preview && <Button type="button" className="button-ghost" onClick={() => photoInput.current?.click()}>Change photo</Button>}<small>Only photographs added here are sent to the configured image service.</small></div>
          {preview && <input ref={photoInput} hidden aria-label="Hazard photograph" type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => changeFile(e.target.files?.[0] || null)} />}
          <input ref={(node) => bindInitialPicker(node, "camera")} hidden tabIndex={-1} aria-label="Camera photograph" type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onChange={(e) => changeFile(e.target.files?.[0] || null)} />
        </div>
        {file && <div className={`photo-analysis-state ${detected ? "photo-analysis-success" : ""}`} role="status" aria-live="polite">
          {photoBusy ? <><RefreshCw size={18} className="spin" /><div><strong>{photoState === "uploading" ? "Uploading your photo…" : "Checking the photograph…"}</strong><p>{photoState === "uploading" ? "Please keep this form open." : "Waiting for the image service. A result appears only after it responds."}</p></div></> :
            <>{detected ? <CheckCircle2 size={19} /> : <TriangleAlert size={19} />}<div><strong>{detected ? "Photo checked — review the suggestion below" : imageExamined ? "Photo checked — the issue needs your review" : "Photo detection is unavailable"}</strong><p>{photoError || analysis?.summary || "The photograph remains evidence. Choose the issue below or describe it; an authority can review it."}</p>{analysis?.errors?.map((error: Json, index: number) => <p key={index}>{error.message}</p>)}{!detected && <p>{imageExamined ? "Choose the correct issue or replace the photograph if it does not show the problem clearly." : "Your photograph has not been analyzed by an image model. You can still send it for human review."}</p>}<Button type="button" className="button-ghost small" onClick={() => file && void analyzePhoto(file, photoGeneration.current, attachmentId ?? undefined)}>Try detection again</Button></div></>}
        </div>}
        <div className="form-grid top-space"><Field label="Issue category" hint="Check the suggestion. You can correct it or leave it for the authority."><select value={category} onChange={(e) => setCategory(e.target.value)}><option value="">Let the authority decide</option>{CATEGORIES.map((item) => <option key={item}>{item}</option>)}</select></Field><Field label="Report title (optional)"><input maxLength={180} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Add a short name, or use the detected suggestion" /></Field></div>
        <Field label="Description (optional)" hint="Anything else the team should know? You can leave this blank."><textarea maxLength={5000} rows={2} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="For example, water is collecting beside the school gate." /></Field>
        {incident?.attachments?.filter((a) => a.kind !== "completion").map((a) => <Evidence key={a.id} attachment={a} onDelete={() => { if (confirm("Remove this photograph from the report?")) remove.mutate(a.id); }} />)}
      </section>
      <section>
        <div className="section-line"><div className="report-step-heading"><span>02</span><div><h3>Check the problem’s location</h3><p>Your current location is used only after permission. Move the marker if the problem is elsewhere.</p></div></div><Button type="button" className="button-secondary small" pending={gps} onClick={locate}><LocateFixed size={15} />Use GPS</Button></div>
        <p className={`location-feedback ${locationConfirmed ? "confirmed" : ""}`} role="status"><MapPin size={15} />{locationMessage}</p>
        <div className="map-frame"><CivicMap height={230} picker={{ ...mapPosition, onPick: setPoint }} /></div>
        {!locationConfirmed && <p className="map-help">The map starts in Lahore for browsing. No location is selected until you tap the map, enter coordinates, or allow GPS.</p>}
        <div className="form-grid top-space"><Field label="Location name (optional)"><input maxLength={240} value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Street, landmark, or neighbourhood" /></Field><details className="coordinate-details"><summary>Enter coordinates manually</summary><div className="form-grid"><Field label="Latitude"><input type="number" step="any" min={-90} max={90} value={latitude} onChange={(e) => updateCoordinate("latitude", e.target.value)} /></Field><Field label="Longitude"><input type="number" step="any" min={-180} max={180} value={longitude} onChange={(e) => updateCoordinate("longitude", e.target.value)} /></Field></div></details></div>
      </section>
      {action.error && <p className="form-error" role="alert">{action.error.message}</p>}
      <div className="form-footer"><p>{photoBusy ? "Wait for the photo check to finish before sending." : "You’ll receive a reference to track the report. An authority reviews every submission."}</p><Button type="button" className="button-secondary" onClick={onClose}>Cancel</Button><Button type="submit" pending={action.isPending} disabled={photoBusy || analysis?.can_submit === false}>{incident ? "Save report" : "Submit report"}</Button></div>
    </form>
  </Modal>;
}
