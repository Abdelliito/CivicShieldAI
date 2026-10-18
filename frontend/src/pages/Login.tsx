import { useState } from "react";
import {
  ArrowRight,
  CircleCheck,
  Eye,
  EyeOff,
  FileCheck2,
  MapPinned,
  Network,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import { toast } from "sonner";
import { api, json, useApi } from "../lib/api";
import { useAuth } from "../lib/auth";
import { Brand, Button, Field } from "../components/UI";
export function Login() {
  const { login } = useAuth();
  const health = useApi<{ demo_mode: boolean }>("/health");
  const [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [name, setName] = useState(""),
    [register, setRegister] = useState(false),
    [pending, setPending] = useState(false),
    [show, setShow] = useState(false),
    [error, setError] = useState("");
  async function submit(e?: React.FormEvent, demo?: string) {
    e?.preventDefault();
    setPending(true);
    setError("");
    try {
      if (register && !demo)
        await api("/auth/register", {
          method: "POST",
          body: json({ name, email, password }),
        });
      await login(
        demo ? `${demo}@civicshield.demo` : email,
        demo ? "CivicDemo!2026" : password,
      );
      toast.success("Welcome to CivicShield AI");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sign in");
    } finally {
      setPending(false);
    }
  }
  return (
    <div className="login-page">
      <div className="login-story">
        <Brand />
        <div className="login-story-content">
          <div className="shield-large">
            <ShieldCheck size={65} strokeWidth={1} />
          </div>
          <h1>
            A safer city starts
            <br />
            with a clearer picture.
          </h1>
          <p>
            Turn everyday civic reports into coordinated action. Detect hazards,
            understand risk, and keep your community moving.
          </p>
          <div className="login-flow">
            {[
              [
                FileCheck2,
                "Report a hazard",
                "One report can make a difference.",
              ],
              [
                MapPinned,
                "Understand the risk",
                "Local evidence. Transparent intelligence.",
              ],
              [
                Network,
                "Coordinate a response",
                "From citizen report to verified resolution.",
              ],
            ].map(([Icon, title, body]) => {
              const I = Icon as typeof FileCheck2;
              return (
                <div key={String(title)}>
                  <span>
                    <I size={21} />
                  </span>
                  <div>
                    <strong>{String(title)}</strong>
                    <p>{String(body)}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
        <footer>Built for civic resilience · Lahore demonstration</footer>
      </div>
      <div className="login-panel">
        <div className="login-form-wrap">
          <div className="login-icon">
            <UserRound size={24} />
          </div>
          <h2>{register ? "Join your civic community" : "Welcome back"}</h2>
          <p>
            {register
              ? "Create a citizen account to report and track local hazards."
              : "Sign in to your CivicShield workspace."}
          </p>
          <form className="stack" onSubmit={submit}>
            {register && (
              <Field label="Full name">
                <input
                  required
                  minLength={2}
                  autoComplete="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Your name"
                />
              </Field>
            )}
            <Field label="Email address">
              <input
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
              />
            </Field>
            <Field label="Password">
              <div className="password-input">
                <input
                  type={show ? "text" : "password"}
                  required
                  minLength={register ? 10 : 1}
                  autoComplete={register ? "new-password" : "current-password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={
                    register ? "At least 10 characters" : "Enter your password"
                  }
                />
                <button
                  type="button"
                  aria-label={show ? "Hide password" : "Show password"}
                  className="icon-button"
                  onClick={() => setShow(!show)}
                >
                  {show ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </div>
            </Field>
            {error && (
              <p role="alert" className="form-error">
                {error}
              </p>
            )}
            <Button pending={pending} className="login-submit">
              {register ? "Create citizen account" : "Sign in"}
              <ArrowRight size={17} />
            </Button>
          </form>
          <p className="auth-switch">
            {register ? "Already have an account?" : "New to CivicShield?"}{" "}
            <button
              className="text-link"
              onClick={() => {
                setRegister(!register);
                setError("");
              }}
            >
              {register ? "Sign in" : "Create an account"}
            </button>
          </p>
          {health.data?.demo_mode === true && (
            <div className="demo-access">
              <div className="demo-label">
                <span />
                Explore the demonstration
                <span />
              </div>
              <div className="demo-buttons">
                {["citizen", "authority", "worker", "admin"].map((role) => (
                  <Button
                    key={role}
                    className="button-secondary"
                    pending={pending}
                    onClick={() => void submit(undefined, role)}
                  >
                    {role[0].toUpperCase() + role.slice(1)}
                  </Button>
                ))}
              </div>
              <p>
                <CircleCheck size={13} />
                Synthetic Lahore data · separate role based workspaces
              </p>
            </div>
          )}
        </div>
        <footer>
          AI supports human decisions. It does not replace emergency services.
        </footer>
      </div>
    </div>
  );
}
