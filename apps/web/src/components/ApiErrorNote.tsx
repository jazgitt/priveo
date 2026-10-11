import { ApiError } from "../api/client";

/** Shows an API error envelope: its message, then each field's problem. */
export function ApiErrorNote({ error }: { error: unknown }) {
  if (!error) return null;
  const known = error instanceof ApiError;
  const fields = known ? Object.entries(error.fields) : [];
  return (
    <div className="form-error" role="alert">
      <p style={{ margin: 0 }}>{known ? error.message : "Something went wrong. Please try again."}</p>
      {fields.length > 0 && (
        <ul style={{ margin: "0.25rem 0 0", paddingLeft: "1.25rem" }}>
          {fields.map(([k, v]) => <li key={k}>{k}: {v}</li>)}
        </ul>
      )}
    </div>
  );
}
