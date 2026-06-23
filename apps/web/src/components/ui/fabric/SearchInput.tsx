/**
 * SearchInput — Icon-prefixed search field.
 * Migrated from WfPrimitives shim.
 */
import { Input } from "@/components/ui/input";
import { Search } from "lucide-react";
import type { ChangeEvent } from "react";

export interface SearchInputProps {
  placeholder?: string;
  value?: string;
  onChange?: (e: ChangeEvent<HTMLInputElement>) => void;
}

export function SearchInput({ placeholder, value, onChange }: SearchInputProps) {
  return (
    <div className="relative flex items-center">
      <Search className="absolute left-3 h-4 w-4 text-muted-foreground" />
      <Input
        type="text"
        value={value || ""}
        onChange={onChange}
        placeholder={placeholder ?? "Search…"}
        className="pl-9 h-8 vf-text-body-s"
      />
    </div>
  );
}
