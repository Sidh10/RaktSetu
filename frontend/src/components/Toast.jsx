import { useEffect } from "react";

export default function Toast({ title, text, error, onClose }) {
  useEffect(() => {
    const id = setTimeout(onClose, error || text ? 9000 : 5000);
    return () => clearTimeout(id);
  }, [title, text, error, onClose]);
  return (
    <div className={`toast ${error ? "error" : ""}`} role={error ? "alert" : "status"} onClick={onClose}>
      <b>{title}</b>
      {text}
    </div>
  );
}

export function errorToast(e, what) {
  const status = e.status ? `${e.status} ${e.code}` : "error";
  return { error: true, title: `${what}: refused (${status})`, text: e.message };
}
