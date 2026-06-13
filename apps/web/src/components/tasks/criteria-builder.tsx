"use client";

import { CriteriaConfig, CriteriaRule } from "@/lib/api";
import { useState } from "react";

const RULE_TYPES = [
  { value: "field_equals", label: "字段等于" },
  { value: "field_exists", label: "字段存在" },
  { value: "field_not_exists", label: "字段不存在" },
  { value: "status_in", label: "状态在列表" },
] as const;

const inputClass = "w-full border border-gray-300 rounded-md px-2 py-1.5 text-sm";

interface Props {
  value: CriteriaConfig;
  onChange: (v: CriteriaConfig) => void;
}

export function CriteriaBuilder({ value, onChange }: Props) {
  const [mode, setMode] = useState<"visual" | "json">("visual");
  const [jsonText, setJsonText] = useState("");
  const [jsonError, setJsonError] = useState("");

  const rules = value.rules || [];

  const updateRules = (next: CriteriaRule[]) => {
    onChange({ ...value, rules: next, match: value.match || "all" });
  };

  const addRule = () => {
    updateRules([...rules, { type: "field_equals", path: "", value: true }]);
  };

  const updateRule = (idx: number, patch: Partial<CriteriaRule>) => {
    updateRules(rules.map((r, i) => (i === idx ? { ...r, ...patch } : r)));
  };

  const removeRule = (idx: number) => {
    updateRules(rules.filter((_, i) => i !== idx));
  };

  const switchToJson = () => {
    setJsonText(JSON.stringify(value, null, 2));
    setJsonError("");
    setMode("json");
  };

  const applyJson = () => {
    try {
      const parsed = JSON.parse(jsonText) as CriteriaConfig;
      onChange(parsed);
      setJsonError("");
      setMode("visual");
    } catch {
      setJsonError("JSON 格式无效");
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-700">完成标准</span>
        <div className="flex gap-2 text-xs">
          <button
            type="button"
            onClick={() => setMode("visual")}
            className={mode === "visual" ? "text-indigo-600 font-medium" : "text-gray-500"}
          >
            可视化
          </button>
          <button type="button" onClick={switchToJson} className={mode === "json" ? "text-indigo-600 font-medium" : "text-gray-500"}>
            JSON
          </button>
        </div>
      </div>

      {mode === "visual" ? (
        <>
          <div className="flex items-center gap-2 text-sm">
            <label className="text-gray-600">匹配模式</label>
            <select
              className={inputClass + " w-auto"}
              value={value.match || "all"}
              onChange={(e) => onChange({ ...value, match: e.target.value as "all" | "any" })}
            >
              <option value="all">全部满足 (all)</option>
              <option value="any">任一满足 (any)</option>
            </select>
          </div>
          {rules.map((rule, idx) => (
            <div key={idx} className="grid grid-cols-12 gap-2 items-start border rounded p-2 bg-gray-50">
              <select
                className={inputClass + " col-span-3"}
                value={rule.type}
                onChange={(e) => updateRule(idx, { type: e.target.value })}
              >
                {RULE_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
              {rule.type !== "status_in" && (
                <input
                  className={inputClass + " col-span-3"}
                  placeholder="字段路径"
                  value={rule.path || ""}
                  onChange={(e) => updateRule(idx, { path: e.target.value })}
                />
              )}
              {rule.type === "field_equals" && (
                <input
                  className={inputClass + " col-span-4"}
                  placeholder="期望值"
                  value={String(rule.value ?? "")}
                  onChange={(e) => {
                    let v: unknown = e.target.value;
                    if (v === "true") v = true;
                    else if (v === "false") v = false;
                    else if (!isNaN(Number(v)) && v !== "") v = Number(v);
                    updateRule(idx, { value: v });
                  }}
                />
              )}
              {rule.type === "status_in" && (
                <input
                  className={inputClass + " col-span-7"}
                  placeholder="success,completed"
                  value={(rule.values || []).join(",")}
                  onChange={(e) =>
                    updateRule(idx, {
                      values: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
                    })
                  }
                />
              )}
              <button type="button" onClick={() => removeRule(idx)} className="col-span-1 text-red-500 text-sm">
                ×
              </button>
            </div>
          ))}
          <button type="button" onClick={addRule} className="text-sm text-indigo-600 hover:text-indigo-800">
            + 添加规则
          </button>
        </>
      ) : (
        <>
          <textarea
            className={inputClass + " font-mono text-xs h-40"}
            value={jsonText}
            onChange={(e) => setJsonText(e.target.value)}
          />
          {jsonError && <p className="text-xs text-red-600">{jsonError}</p>}
          <button type="button" onClick={applyJson} className="text-sm bg-indigo-600 text-white px-3 py-1 rounded">
            应用 JSON
          </button>
        </>
      )}
    </div>
  );
}
