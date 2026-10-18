import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Camera, LocateFixed, UploadCloud, X, MapPin } from "lucide-react";
import { toast } from "sonner";
import { api, json, upload, useAction } from "../lib/api";
import type { Incident } from "../lib/types";
import { Button, Evidence, Field, Modal } from "./UI";
import { CivicMap } from "./Map";
export function ReportForm({
  open,
  onClose,
  incident,
  onSaved,
}: {
  open: boolean;
  onClose: () => void;
  incident?: Incident;
  onSaved?: (id: number) => void;
}) {
  const photoInput = useRef<HTMLInputElement>(null);
  const cameraInput = useRef<HTMLInputElement>(null);
  const [title, setTitle] = useState(incident?.title || ""),
    [description, setDescription] = useState(incident?.description || ""),
    [location, setLocation] = useState(incident?.location_name || ""),
    [latitude, setLatitude] = useState(String(incident?.latitude ?? 31.5204)),
    [longitude, setLongitude] = useState(String(incident?.longitude ?? 74.3587)),
    [mapPosition, setMapPosition] = useState({ latitude: incident?.latitude ?? 31.5204, longitude: incident?.longitude ?? 74.3587 }),
    [file, setFile] = useState<File | null>(null),
    [preview, setPreview] = useState(""),
    [gps, setGps] = useState(false);
  const action = useAction(
    async () => {
      const lat = Number(latitude), lng = Number(longitude);
      if (!latitude.trim() || !longitude.trim() || !Number.isFinite(lat) || !Number.isFinite(lng) || lat < -90 || lat > 90 || lng < -180 || lng > 180)
        throw new Error("Enter valid latitude and longitude, or select the hazard location on the map.");
      const attachmentIds =
        incident?.attachments
          ?.filter((a) => a.kind !== "completion")
          .map((a) => a.id) || [];
      if (file) {
        const image = await upload(file);
        attachmentIds.push(image.id);
      }
      const result = await api<Incident>(
        incident ? `/reports/${incident.id}` : "/reports",
        {
          method: incident ? "PATCH" : "POST",
          body: json({
            title,
            description,
            location_name: location,
            latitude: lat,
            longitude: lng,
            attachment_ids: attachmentIds,
          }),
        },
      );
      onSaved?.(result.id);
      onClose();
      return result;
    },
    incident
      ? "Report updated"
      : "Report submitted. Analysis is ready for review.",
  );
  const remove = useAction(
    (id: number) => api(`/uploads/${id}`, { method: "DELETE" }),
    "Photo removed",
  );
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);
  function updateCoordinate(axis: "latitude" | "longitude", value: string) {
    if (axis === "latitude") setLatitude(value); else setLongitude(value);
    const coordinate = Number(value), limit = axis === "latitude" ? 90 : 180;
    if (value.trim() && Number.isFinite(coordinate) && Math.abs(coordinate) <= limit)
      setMapPosition((current) => ({ ...current, [axis]: coordinate }));
  }
  function changeFile(next: File | null) {
    if (next && !next.type.startsWith("image/"))
      return toast.error("Please select an image file.");
    if (next && next.size > 8 * 1024 * 1024)
      return toast.error("Images must be smaller than 8 MB.");
    setFile(next);
    setPreview(next ? URL.createObjectURL(next) : "");
    if (!next && photoInput.current) photoInput.current.value = "";
    if (!next && cameraInput.current) cameraInput.current.value = "";
  }
  function locate() {
    if (!navigator.geolocation)
      return toast.error("Location is unavailable. Select a point on the map.");
    setGps(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLatitude(String(position.coords.latitude));
        setLongitude(String(position.coords.longitude));
        setMapPosition({ latitude: position.coords.latitude, longitude: position.coords.longitude });
        setGps(false);
        toast.success("Your location has been added.");
      },
      () => {
        setGps(false);
        toast.error(
          "Location access was unavailable. Select your location on the map.",
        );
      },
    );
  }
  function submit(event: FormEvent) {
    event.preventDefault();
    action.mutate(undefined);
  }
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={incident ? "Edit your report" : "Report a civic hazard"}
      description="Tell us what you see. CivicShield will help route your report for human review."
      wide
    >
      <form onSubmit={submit} className="report-form">
        <div className="report-step-heading"><span>01</span><div><h3>Describe the hazard</h3><p>A clear report helps the right team respond.</p></div></div>
        <div className="form-grid">
          <Field label="Report title">
            <input
              required
              minLength={5}
              maxLength={180}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Blocked drain on Main Boulevard"
            />
          </Field>
          <Field label="Location name">
            <input
              required
              minLength={3}
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="Street, landmark, or neighbourhood"
            />
          </Field>
        </div>
        <Field
          label="Description"
          hint="Describe the hazard, its surroundings, and any immediate safety concern."
        >
          <textarea
            required
            minLength={15}
            maxLength={5000}
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Water is pooling around an obstructed drain near the intersection…"
          />
        </Field>
        <div className="form-grid">
          <div>
            <div className="report-step-heading"><span>02</span><div><h3>Photograph</h3><p>Add evidence from a safe distance.</p></div></div>
            <label className="upload-zone">
              <UploadCloud size={25} />
              <strong>{file ? file.name : "Choose a photograph"}</strong>
              <span>JPG, PNG, WebP · up to 8 MB</span>
              <input
                ref={photoInput}
                aria-label="Hazard photograph"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={(e) => changeFile(e.target.files?.[0] || null)}
              />
            </label>
            <div className="inline-actions" style={{ marginTop: 10 }}>
              <Button type="button" className="button-secondary small" onClick={() => cameraInput.current?.click()}><Camera size={16} />Take photo</Button>
              <small className="muted">Use your camera or choose an existing photograph.</small>
            </div>
            <input ref={cameraInput} hidden tabIndex={-1} aria-label="Camera photograph" type="file" accept="image/*" capture="environment" onChange={(e) => changeFile(e.target.files?.[0] || null)} />
            {preview && (
              <div className="selected-image">
                <img src={preview} alt="Selected hazard preview" />
                <button
                  type="button"
                  aria-label="Remove selected photograph"
                  className="icon-button"
                  onClick={() => changeFile(null)}
                >
                  <X size={18} />
                </button>
              </div>
            )}
            {incident?.attachments
              ?.filter((a) => a.kind !== "completion")
              .map((a) => (
                <Evidence
                  key={a.id}
                  attachment={a}
                  onDelete={() => {
                    if (confirm("Remove this photograph from the report?"))
                      remove.mutate(a.id);
                  }}
                />
              ))}
          </div>
          <div>
            <div className="section-line">
              <div className="report-step-heading"><span>03</span><div><h3>Hazard location</h3><p>Place the marker where you saw it.</p></div></div>
              <Button
                type="button"
                className="button-ghost small"
                pending={gps}
                onClick={locate}
              >
                <LocateFixed size={15} />
                Use GPS
              </Button>
            </div>
            <div className="map-frame">
              <CivicMap
                height={220}
                picker={{
                  ...mapPosition,
                  onPick: (lat, lng) => {
                    const location = { latitude: Number(lat.toFixed(6)), longitude: Number(lng.toFixed(6)) };
                    setLatitude(String(location.latitude));
                    setLongitude(String(location.longitude));
                    setMapPosition(location);
                  },
                }}
              />
            </div>
            <p className="map-help">
              <MapPin size={12} />
              Click the map to set or correct your location.
            </p>
            <div className="form-grid">
              <Field label="Latitude">
                <input
                  type="number"
                  step="any"
                  required
                  min={-90}
                  max={90}
                  value={latitude}
                  onChange={(e) => updateCoordinate("latitude", e.target.value)}
                />
              </Field>
              <Field label="Longitude">
                <input
                  type="number"
                  step="any"
                  required
                  min={-180}
                  max={180}
                  value={longitude}
                  onChange={(e) => updateCoordinate("longitude", e.target.value)}
                />
              </Field>
            </div>
          </div>
        </div>
        <div className="form-footer">
          <p>Your report is saved securely and reviewed by an authority.</p>
          <Button type="button" className="button-secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" pending={action.isPending}>
            {incident ? "Save report" : "Submit report"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
