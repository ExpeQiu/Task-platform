"use client";

import { AppShell } from "@/components/layout/app-shell";
import { api, Skill, SkillCreate } from "@/lib/api";
import { useEffect, useState } from "react";

const inputClass = "w-full border border-gray-300 rounded-md px-3 py-2 text-sm";

const EMPTY: SkillCreate = { name: "", description: "", instructions: "" };

export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [form, setForm] = useState<SkillCreate>({ ...EMPTY });
  const [showForm, setShowForm] = useState(false);
  const [message, setMessage] = useState("");

  const load = () => api.listSkills().then((r) => setSkills(r.items)).catch(console.error);
  useEffect(() => { load(); }, []);

  const create = async () => {
    if (!form.name.trim()) {
      setMessage("请填写 Skill 名称");
      return;
    }
    try {
      await api.createSkill(form);
      setForm({ ...EMPTY });
      setShowForm(false);
      setMessage("Skill 已创建");
      load();
    } catch (e) {
      setMessage(String(e));
    }
  };

  return (
    <AppShell title="Skill / Playbook">
      {message && (
        <div className="mb-4 bg-indigo-50 text-indigo-800 px-4 py-2 rounded text-sm">{message}</div>
      )}
      <div className="flex justify-between mb-6">
        <p className="text-sm text-gray-600">可复用任务指令资产，创建任务时可关联 Skill。</p>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm hover:bg-indigo-700"
        >
          新建 Skill
        </button>
      </div>

      {showForm && (
        <div className="mb-6 bg-white p-4 rounded-lg border space-y-3">
          <input
            className={inputClass}
            placeholder="名称（唯一）"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <input
            className={inputClass}
            placeholder="描述"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
          <textarea
            className={inputClass}
            rows={6}
            placeholder="Instructions / Playbook 正文"
            value={form.instructions}
            onChange={(e) => setForm({ ...form, instructions: e.target.value })}
          />
          <div className="flex gap-2">
            <button onClick={create} className="bg-indigo-600 text-white px-4 py-2 rounded text-sm">保存</button>
            <button onClick={() => setShowForm(false)} className="border px-4 py-2 rounded text-sm">取消</button>
          </div>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {skills.map((s) => (
          <div key={s.id} className="bg-white border rounded-lg p-4 shadow-sm">
            <div className="flex justify-between items-start">
              <h3 className="font-medium">{s.name}</h3>
              <span className="text-xs font-mono text-gray-400">{s.id.slice(0, 8)}</span>
            </div>
            <p className="text-sm text-gray-600 mt-1">{s.description || "无描述"}</p>
            <pre className="text-xs bg-gray-50 p-2 rounded mt-2 max-h-24 overflow-auto whitespace-pre-wrap">
              {s.instructions || "（无 instructions）"}
            </pre>
          </div>
        ))}
        {skills.length === 0 && <p className="text-gray-500 col-span-2">暂无 Skill，点击新建。</p>}
      </div>
    </AppShell>
  );
}
