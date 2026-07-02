import { useState, useEffect, useContext } from "react"
import { ToastContext } from "../Toast/ToastContext";
import type { Target } from "../../pages/add-target/page"
import { get_targets, type TargetActiveState } from "../../queries/targets";
import TargetRow from "./Target";
import { Loader2 } from "lucide-react";
import useDebounced from "../../hooks/useDebounced";
import Pagination from "../Pagination/Pagination";
import Switch from "../Switch/Switch";

export default function TargetList(): React.ReactNode {
  const [targets, setTargets] = useState<Target[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [search, setSearch] = useState<string>("");
  const [page, setPage] = useState<number>(1);
  const perPage = 10;
  const [total, setTotal] = useState<number>(0);
  const [active, setActive] = useState<TargetActiveState>("both");
  const debouncedSearch = useDebounced(search, 300);
  const toast = useContext(ToastContext);

  useEffect(() => {
    setLoading(true);
    get_targets({ page, per_page: perPage, search: debouncedSearch.trim(), active: active })
      .then((payload) => {
        setTargets(payload.items);
        setTotal(payload.total);
      })
      .catch((e) => {
        const message = e instanceof Error ? e.message : "Failed to fetch targets";
        toast?.error(message);
      })
      .finally(() => {
        setLoading(false);
      })
  }, [debouncedSearch, active, page, perPage])

  return (
    <div className="flex flex-1 min-h-0 flex-col">
      <form className="mb-6 flex place-content-between items-center gap-6">
        <div className="flex flex-col grow">
          <input onChange={(e) => setSearch(e.target.value)} value={search} placeholder="Search targets..." id="search" name="search" type="text" className="text-input" />
        </div>
        <div className="flex gap-2 items-center">
          <Switch id="is_active" checked={active === "true"} onCheckedChange={(checked) => setActive(checked ? "true" : "both")} />
          <label htmlFor="is_active" className="text-sm">Active only</label>
        </div>
      </form>
      <div className="card flex-1 min-h-0 overflow-auto">
        {loading ?
          <div className="flex h-full items-center justify-center">
            <Loader2 size={18} className="animate-spin" />
          </div>
          :
          targets.map((t) => TargetRow(t))}
      </div>
      <div className="mx-auto">
        <Pagination range={Math.ceil(total / perPage)} page={page} onPageChange={setPage} />
      </div>
    </div>
  )
}
