import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StatusFilter } from "./StatusFilter";

describe("StatusFilter", () => {
  it("renders options and calls onChange", async () => {
    const onChange = vi.fn();
    render(
      <StatusFilter
        label="Status"
        value="all"
        options={[
          { value: "all", label: "All" },
          { value: "active", label: "Active" },
        ]}
        onChange={onChange}
      />
    );

    const select = screen.getByLabelText("Status");
    await userEvent.selectOptions(select, "active");
    expect(onChange).toHaveBeenCalledWith("active");
  });
});
