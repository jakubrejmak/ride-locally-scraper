import { useState } from "react";

interface PaginationProps {
  range: number;
  displayInput?: boolean;
  iconPrev?: string;
  iconNext?: string;
  page?: number;
  onPageChange?: (page: number) => void;
}

export default function Pagination({
  range,
  displayInput = true,
  iconPrev = "Prev",
  iconNext = "Next",
  page,
  onPageChange,
}: PaginationProps): React.ReactNode {
  const [internalPage, setInternalPage] = useState<number>(1);
  const [manualPage, setManualPage] = useState<string>("");
  const [isEditingManual, setIsEditingManual] = useState<boolean>(false);

  const totalPages = Math.max(1, Math.floor(range));
  const isControlled = page !== undefined;
  const currentPage = Math.min(Math.max(1, Math.floor(page ?? internalPage)), totalPages);

  function setPage(next: number) {
    const normalized = Math.min(Math.max(1, Math.floor(next)), totalPages);

    if (!isControlled) {
      setInternalPage(normalized);
    }

    setManualPage(String(normalized));
    onPageChange?.(normalized);
  }

  const pages = Array.from({ length: totalPages }, (_, i) => i + 1);

  return (
    <div className="mt-4 flex flex-wrap items-center justify-end gap-2">
      <button
        type="button"
        onClick={() => setPage(currentPage - 1)}
        disabled={currentPage <= 1}
        className="btn-secondary h-9 px-3 py-1"
      >
        {iconPrev}
      </button>

      {pages.map((p) => (
        <button
          key={p}
          type="button"
          onClick={() => setPage(p)}
          className={p === currentPage
            ? "btn-primary h-9 w-9 justify-center p-0 [font-variant-numeric:tabular-nums]"
            : "btn-secondary h-9 w-9 justify-center p-0 [font-variant-numeric:tabular-nums]"
          }
        >
          {p}
        </button>
      ))}

      {displayInput ? (
        <input
          aria-label="Custom page"
          inputMode="numeric"
          pattern="[0-9]*"
          value={isEditingManual ? manualPage : String(currentPage)}
          onFocus={() => {
            setIsEditingManual(true);
            setManualPage(String(currentPage));
          }}
          onChange={(e) => setManualPage(e.target.value.replace(/\D/g, ""))}
          onBlur={() => {
            if (manualPage) {
              setPage(Number(manualPage));
            }

            setIsEditingManual(false);
            setManualPage("");
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              if (manualPage) {
                setPage(Number(manualPage));
              }
              setIsEditingManual(false);
              setManualPage("");
            }
          }}
          className="text-input h-9 w-20"
          placeholder="#"
        />
      ) : null}

      <button
        type="button"
        onClick={() => setPage(currentPage + 1)}
        disabled={currentPage >= totalPages}
        className="btn-secondary h-9 px-3 py-1"
      >
        {iconNext}
      </button>
    </div>
  );
}
