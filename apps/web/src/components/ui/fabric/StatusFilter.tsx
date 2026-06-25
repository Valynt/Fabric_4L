import * as React from "react";

export interface StatusFilterOption {
  value: string;
  label: string;
}

export interface StatusFilterProps {
  label: string;
  value: string;
  options: StatusFilterOption[];
  onChange: (value: string) => void;
}

export function StatusFilter({ label, value, options, onChange }: StatusFilterProps) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-sm font-medium">{label}</span>
      <select
        aria-label={label}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="border rounded px-2 py-1 text-sm"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
