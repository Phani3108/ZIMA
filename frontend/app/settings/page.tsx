"use client";

import { useEffect, useState } from "react";
import { CheckCircle, Circle, ChevronDown, ChevronUp, Save, Trash2 } from "lucide-react";
import clsx from "clsx";

type KeyDef = { name: string; label: string; secret: boolean };
type Integration = {
  name: string;
  label: string;
  description: string;
  configured: boolean;
  key_definitions: KeyDef[];
};

export default function SettingsPage() {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  const [forms, setForms] = useState<Record<string, Record<string, string>>>({});
  const [saving, setSaving] = useState<string | null>(null);
  const [message, setMessage] = useState<{ name: string; text: string; ok: boolean } | null>(null);

  useEffect(() => {
    fetch("/api/settings/integrations")
      .then((r) => r.json())
      .then(setIntegrations)
      .catch(console.error);
  }, []);

  const setField = (integration: string, key: string, value: string) => {
    setForms((f) => ({ ...f, [integration]: { ...(f[integration] || {}), [key]: value } }));
  };

  const save = async (name: string) => {
    setSaving(name);
    const keys = forms[name] || {};
    const r = await fetch(`/api/settings/integrations/${name}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keys }),
    });
    const data = await r.json();
    setSaving(null);
    setMessage({ name, text: data.ok ? "Saved." : data.detail || "Error", ok: data.ok });
    if (data.ok) {
      setIntegrations((prev) => prev.map((i) => i.name === name ? { ...i, configured: true } : i));
    }
    setTimeout(() => setMessage(null), 3000);
  };

  const remove = async (name: string) => {
    if (!confirm(`Remove all keys for ${name}?`)) return;
    await fetch(`/api/settings/integrations/${name}`, { method: "DELETE" });
    setIntegrations((prev) => prev.map((i) => i.name === name ? { ...i, configured: false } : i));
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-xl font-semibold text-gray-800 mb-2">Integrations & API Keys</h1>
      <p className="text-sm text-gray-500 mb-6">
        Keys are encrypted with Fernet and stored in Azure Key Vault + PostgreSQL. They are never displayed after saving.
      </p>

      <div className="space-y-3">
        {integrations.map((intg) => (
          <div key={intg.name} className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            <button
              onClick={() => setOpen(open === intg.name ? null : intg.name)}
              className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50"
            >
              <div className="flex items-center gap-3">
                {intg.configured
                  ? <CheckCircle size={18} className="text-green-500" />
                  : <Circle size={18} className="text-gray-300" />
                }
                <div className="text-left">
                  <div className="font-medium text-gray-800 text-sm">{intg.label}</div>
                  <div className="text-xs text-gray-400">{intg.description}</div>
                </div>
              </div>
              {open === intg.name ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>

            {open === intg.name && (
              <div className="px-4 pb-4 space-y-3 border-t bg-gray-50">
                {intg.key_definitions.map((kd) => (
                  <div key={kd.name}>
                    <label className="block text-xs font-medium text-gray-600 mb-1">{kd.label}</label>
                    <input
                      type={kd.secret ? "password" : "text"}
                      placeholder={intg.configured ? "••••••••" : kd.label}
                      className="w-full border rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand"
                      onChange={(e) => setField(intg.name, kd.name, e.target.value)}
                    />
                  </div>
                ))}

                {message?.name === intg.name && (
                  <p className={clsx("text-xs", message.ok ? "text-green-600" : "text-red-600")}>{message.text}</p>
                )}

                <div className="flex gap-2 pt-1">
                  <button
                    onClick={() => save(intg.name)}
                    disabled={saving === intg.name}
                    className="flex items-center gap-1 bg-brand hover:bg-blue-700 text-white text-xs px-3 py-1.5 rounded-lg disabled:opacity-50"
                  >
                    <Save size={12} /> {saving === intg.name ? "Saving..." : "Save"}
                  </button>
                  {intg.configured && (
                    <button
                      onClick={() => remove(intg.name)}
                      className="flex items-center gap-1 text-red-600 hover:text-red-700 text-xs px-3 py-1.5 rounded-lg border border-red-200 hover:bg-red-50"
                    >
                      <Trash2 size={12} /> Remove
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
