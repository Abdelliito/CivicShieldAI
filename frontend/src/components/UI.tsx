import type { ReactNode, ReactElement } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { AlertCircle, Check, LoaderCircle, ShieldCheck, X } from "lucide-react";
import {
  Children,
  cloneElement,
  isValidElement,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";
import { attachmentBlob } from "../lib/api";
import type { Attachment } from "../lib/types";
import { statusLabel } from "../lib/types";
export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className="brand">
      <span className="brand-symbol">
        <ShieldCheck size={32} strokeWidth={1.6} aria-hidden="true" />
      </span>
      {!compact && (
        <div>
          CivicShield<span className="brand-ai"> AI</span>
          <small>Civic Atlas</small>
        </div>
      )}
    </div>
  );
}
export function Badge({ children }: { children: ReactNode }) {
  const c = String(children).toLowerCase().replaceAll(" ", "-");
  return (
    <span className={`badge badge-${c}`} title={String(children)}>
      <i />
      {typeof children === "string" ? statusLabel(children) : children || "Pending"}
    </span>
  );
}
export function Loading({
  text = "Loading civic intelligence…",
}: {
  text?: string;
}) {
  return (
    <div className="loading">
      <LoaderCircle className="spin" size={24} />
      {text}
    </div>
  );
}
export function ErrorState({
  error,
  retry,
}: {
  error: unknown;
  retry?: () => void;
}) {
  return (
    <div className="error-state">
      <AlertCircle size={24} />
      <h3>Unable to load this view</h3>
      <p>
        {error instanceof Error
          ? error.message
          : "Please check the backend connection."}
      </p>
      {retry && (
        <button className="button" onClick={retry}>
          Try again
        </button>
      )}
    </div>
  );
}
export function Empty({
  title = "Nothing here yet",
  body = "New activity will appear here.",
}: {
  title?: string;
  body?: string;
}) {
  return (
    <div className="empty">
      <Check size={26} />
      <h3>{title}</h3>
      <p>{body}</p>
    </div>
  );
}
export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  wide = false,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: ReactNode;
  wide?: boolean;
}) {
  const returnFocus = useRef<HTMLElement | SVGElement | null>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  return (
    <Dialog.Root open={open} onOpenChange={(v) => !v && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content
          ref={contentRef}
          className={`dialog-content ${wide ? "dialog-wide" : ""}`}
          onOpenAutoFocus={() => {
            const active = document.activeElement;
            if ((active instanceof HTMLElement || active instanceof SVGElement) && active !== document.body && !contentRef.current?.contains(active))
              returnFocus.current = active;
          }}
          onCloseAutoFocus={(event) => {
            event.preventDefault();
            if (returnFocus.current?.isConnected)
              returnFocus.current.focus({ preventScroll: true });
          }}
        >
          <div className="dialog-heading">
            <div>
              <Dialog.Title>{title}</Dialog.Title>
              <Dialog.Description>
                {description || "Review the details and save your changes."}
              </Dialog.Description>
            </div>
            <Dialog.Close aria-label="Close dialog" className="icon-button">
              <X size={20} />
            </Dialog.Close>
          </div>
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
export function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}) {
  const id = useId();
  function connect(nodes: ReactNode): ReactNode {
    return Children.map(nodes, (node) => {
      if (!isValidElement(node)) return node;
      const element = node as ReactElement<Record<string, any>>;
      if (
        typeof element.type === "string" &&
        ["input", "textarea", "select"].includes(element.type)
      )
        return cloneElement(element, {
          id,
          "aria-labelledby": `${id}-label`,
          "aria-describedby": hint ? `${id}-hint` : undefined,
        });
      return element.props.children
        ? cloneElement(element, {}, connect(element.props.children))
        : element;
    });
  }
  return (
    <div className="field">
      <label htmlFor={id} id={`${id}-label`}>
        {label}
      </label>
      {connect(children)}
      {hint && <small id={`${id}-hint`}>{hint}</small>}
    </div>
  );
}
export function Button({
  pending = false,
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { pending?: boolean }) {
  return (
    <button
      {...props}
      disabled={pending || props.disabled}
      aria-busy={pending || undefined}
      className={`button ${props.className || ""}`}
    >
      {pending ? <LoaderCircle size={16} className="spin" /> : null}
      {children}
    </button>
  );
}
export function JsonDetails({ data }: { data: unknown }) {
  if (!data) return <p className="muted">No information recorded.</p>;
  return (
    <details className="structured-evidence">
      <summary>View structured evidence</summary>
      <pre className="json-details">{JSON.stringify(data, null, 2)}</pre>
    </details>
  );
}
export function Evidence({
  attachment,
  onDelete,
}: {
  attachment: Attachment;
  onDelete?: () => void;
}) {
  const [src, setSrc] = useState("");
  const [error, setError] = useState(false);
  useEffect(() => {
    let active = true;
    let url = "";
    attachmentBlob(attachment.id)
      .then((value) => {
        url = value;
        if (active) setSrc(value);
      })
      .catch(() => setError(true));
    return () => {
      active = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [attachment.id]);
  return (
    <div className="evidence">
      {src ? (
        <a href={src} target="_blank" rel="noreferrer">
          <img src={src} alt={attachment.filename} />
        </a>
      ) : (
        <div className="evidence-loading">
          {error ? "Image unavailable" : "Loading image…"}
        </div>
      )}
      <div>
        <span title={attachment.filename}>{attachment.filename}</span>
        {onDelete && (
          <button
            className="icon-button danger-text"
            type="button"
            aria-label={`Remove ${attachment.filename}`}
            onClick={onDelete}
          >
            <X size={15} />
          </button>
        )}
      </div>
      {attachment.kind === "completion" && <small>Completion evidence</small>}
    </div>
  );
}
