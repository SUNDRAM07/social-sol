import { useState } from "react";
import * as Dropdown from "@radix-ui/react-dropdown-menu";
import { DayPicker } from "react-day-picker";
import "react-day-picker/style.css";

function DatePicker({ value, onChange }) {
  const [open, setOpen] = useState(false);
  const dateValue = value ? new Date(value) : undefined;
  return (
    <Dropdown.Root open={open} onOpenChange={setOpen}>
      <Dropdown.Trigger asChild>
        <button className="px-3 py-2 rounded-md border border-gray-300 text-sm bg-white">
          {value || "Select date"}
        </button>
      </Dropdown.Trigger>
      <Dropdown.Portal>
        <Dropdown.Content
          className="bg-white rounded-md shadow-lg p-2 border border-gray-200"
          sideOffset={6}
        >
          <DayPicker
            mode="single"
            selected={dateValue}
            onSelect={(d) => {
              if (d) {
                onChange(d.toISOString().slice(0, 10));
                setOpen(false);
              }
            }}
          />
        </Dropdown.Content>
      </Dropdown.Portal>
    </Dropdown.Root>
  );
}

export default DatePicker;
