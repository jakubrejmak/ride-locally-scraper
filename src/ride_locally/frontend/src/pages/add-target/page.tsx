import { useContext, useEffect, useMemo, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { ArrowLeft, CalendarClock, Loader2, Plus, Trash2, WandSparkles } from "lucide-react";
import { z } from "zod";
import cronstrue from "cronstrue";
import { Popover } from "@base-ui/react/popover";
import { Combobox } from "@base-ui/react/combobox";

import { apiFetch } from "../../api/client";
import Background from "../../components/Background/Background";
import Layout from "../../components/Layout/Layout";
import { ToastContext } from "../../components/Toast/ToastContext";
import useDebounced from "../../hooks/useDebounced";
import Switch from "../../components/Switch/Switch";

const cronPresets = [
  { label: "Hourly", value: "0 * * * *" },
  { label: "Daily", value: "0 9 * * *" },
  { label: "Weekly", value: "0 9 * * 1" },
  { label: "Monthly", value: "0 9 1 * *" },
];

const jsonObjectSchema = z.record(z.string(), z.unknown());

const firecrawlConfigSchema = z.object({
  scrape_method: z.literal("firecrawl"),
  format: z.string().nullable().optional(),
});

const scraplingFetcherSchema = z.enum([
  "AsyncFetcher",
  "DynamicFetcher",
  "StealthyFetcher",
]);

const scraplingSimpleSchema = z
  .object({
    scrape_method: z.literal("scrapling"),
    mode: z.literal("simple"),
    fetcher: scraplingFetcherSchema.optional(),
    selectors: z.array(z.string()).nullable().optional(),
    force_mime: z.string().nullable().optional(),
  })
  .refine(
    (v) =>
      !(
        v.selectors &&
        v.selectors.length > 0 &&
        v.force_mime &&
        v.force_mime.length > 0
      ),
    {
      path: ["force_mime"],
      message:
        "force_mime is meaningless when selectors are set (output is always text/html)",
    }
  );

const scraplingScriptSchema = z.object({
  scrape_method: z.literal("scrapling"),
  mode: z.literal("script"),
  script_path: z.string().min(1),
});

const scraplingConfigSchema = z.discriminatedUnion("mode", [
  scraplingSimpleSchema,
  scraplingScriptSchema,
]);

const scraperConfigSchema = z.discriminatedUnion("scrape_method", [
  firecrawlConfigSchema,
  scraplingConfigSchema,
]);

const preprocessorToolSchema = z.object({
  ref: z.string(),
  params: z.array(jsonObjectSchema).optional(),
});

const preprocessorConfigSchema = z.object({
  tools: z.array(preprocessorToolSchema).nullable().optional(),
});

const llmProviderConfigSchema = z.discriminatedUnion("provider", [
  z.object({
    provider: z.literal("openrouter"),
    model: z.literal("gemini-3-flash-preview"),
    system_prompt: z.string().nullable().optional(),
    user_prompts: z.array(z.string()).optional(),
    api_params: jsonObjectSchema.optional(),
  }),
  z.object({
    provider: z.literal("gemini"),
    model: z.literal("gemini-3-flash-preview"),
    system_prompt: z.string().nullable().optional(),
    user_prompts: z.array(z.string()).optional(),
    api_params: jsonObjectSchema.optional(),
  }),
]);

const llmProcessorConfigSchema = z.object({
  process_method: z.literal("llm"),
  config: llmProviderConfigSchema,
});

const processorConfigSchema = llmProcessorConfigSchema;

const scrTargetConfigSchema = z.object({
  scraper: scraperConfigSchema,
  preprocessor: preprocessorConfigSchema.nullable().optional(),
  processor: processorConfigSchema.nullable().optional(),
});

const newTargetSchema = z.object({
  name: z.string(),
  url: z.string(),
  config: scrTargetConfigSchema,
  is_active: z.boolean(),
  schedule_cron: z.string().nullable().optional(),
  carrier_id: z.number().nullable().optional(),
});

export type NewTarget = z.infer<typeof newTargetSchema>;
export type Target = NewTarget & { id: number };

type Step = 1 | 2 | 3 | 4;
type ScrapeMethod = "firecrawl" | "scrapling";
type ScraplingMode = "simple" | "script";
type LlmProvider = "openrouter" | "gemini";

type ToolDraft = {
  id: string;
  ref: string;
  params: string;
};

const stepLabels: Record<Step, string> = {
  1: "Basics",
  2: "Scraper",
  3: "Pipeline",
  4: "Review",
};

const steps: Step[] = [1, 2, 3, 4];

function parseObjectArray(raw: string): Record<string, unknown>[] | undefined {
  const trimmed = raw.trim();
  if (!trimmed) {
    return undefined;
  }

  const parsed = JSON.parse(trimmed);
  if (!Array.isArray(parsed)) {
    throw new Error("Params must be a JSON array");
  }

  for (const item of parsed) {
    if (typeof item !== "object" || item === null || Array.isArray(item)) {
      throw new Error("Params array must contain only JSON objects");
    }
  }

  return parsed as Record<string, unknown>[];
}

function parseObject(raw: string): Record<string, unknown> | undefined {
  const trimmed = raw.trim();
  if (!trimmed) {
    return undefined;
  }

  const parsed = JSON.parse(trimmed);
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    throw new Error("API params must be a JSON object");
  }

  return parsed as Record<string, unknown>;
}

export default function AddTarget(): React.ReactNode {
  const navigate = useNavigate();
  const toast = useContext(ToastContext);

  const [loading, setLoading] = useState<boolean>(false);
  const [step, setStep] = useState<Step>(1);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState<string>("");
  const [url, setUrl] = useState<string>("");
  const [isActive, setIsActive] = useState<boolean>(true);
  const [carrierId, setCarrierId] = useState<string>("");
  const [cron, setCron] = useState<string>("");

  const [scrapeMethod, setScrapeMethod] = useState<ScrapeMethod>("scrapling");
  const [firecrawlFormat, setFirecrawlFormat] = useState<string>("");
  const [scraplingMode, setScraplingMode] = useState<ScraplingMode>("simple");
  const [scraplingFetcher, setScraplingFetcher] = useState<"AsyncFetcher" | "DynamicFetcher" | "StealthyFetcher">("AsyncFetcher");
  const [scraplingForceMime, setScraplingForceMime] = useState<string>("");
  const [scraplingSelectors, setScraplingSelectors] = useState<string>("");
  const [scriptPath, setScriptPath] = useState<string>("");
  const debouncedScriptPath = useDebounced(scriptPath, 300);
  const [scriptsList, setScriptsList] = useState<string[]>([]);

  const [usePreprocessor, setUsePreprocessor] = useState<boolean>(false);
  const [tools, setTools] = useState<ToolDraft[]>([]);

  const [useProcessor, setUseProcessor] = useState<boolean>(false);
  const [provider, setProvider] = useState<LlmProvider>("openrouter");
  const [systemPrompt, setSystemPrompt] = useState<string>("");
  const [userPrompts, setUserPrompts] = useState<string>("");
  const [apiParamsRaw, setApiParamsRaw] = useState<string>("");

  const cronReadable = useMemo<string | null>(() => {
    if (!cron.trim()) {
      return null;
    }

    try {
      return cronstrue.toString(cron.trim());
    } catch {
      return null;
    }
  }, [cron]);

  function addTool() {
    setTools((current) => [...current, { id: crypto.randomUUID(), ref: "", params: "" }]);
  }

  function removeTool(id: string) {
    setTools((current) => current.filter((tool) => tool.id !== id));
  }

  function updateTool(id: string, patch: Partial<Omit<ToolDraft, "id">>) {
    setTools((current) =>
      current.map((tool) => (tool.id === id ? { ...tool, ...patch } : tool))
    );
  }

  function buildPayload(): NewTarget {
    const scraper = scrapeMethod === "firecrawl"
      ? {
        scrape_method: "firecrawl" as const,
        format: firecrawlFormat.trim() ? firecrawlFormat.trim() : null,
      }
      : scraplingMode === "script"
        ? {
          scrape_method: "scrapling" as const,
          mode: "script" as const,
          script_path: scriptPath.trim(),
        }
        : {
          scrape_method: "scrapling" as const,
          mode: "simple" as const,
          fetcher: scraplingFetcher,
          force_mime: scraplingForceMime.trim() ? scraplingForceMime.trim() : null,
          selectors: scraplingSelectors.trim()
            ? scraplingSelectors
              .split("\n")
              .map((s) => s.trim())
              .filter(Boolean)
            : null,
        };

    const preprocessor = usePreprocessor
      ? {
        tools: tools.map((tool) =>
          preprocessorToolSchema.parse({
            ref: tool.ref.trim(),
            params: parseObjectArray(tool.params),
          })
        ),
      }
      : null;

    const processor = useProcessor
      ? {
        process_method: "llm" as const,
        config: {
          provider,
          model: "gemini-3-flash-preview" as const,
          system_prompt: systemPrompt.trim() ? systemPrompt.trim() : null,
          user_prompts: userPrompts
            .split("\n")
            .map((p) => p.trim())
            .filter(Boolean),
          api_params: parseObject(apiParamsRaw),
        },
      }
      : null;

    return newTargetSchema.parse({
      name: name.trim(),
      url: url.trim(),
      is_active: isActive,
      carrier_id: carrierId.trim() ? Number(carrierId) : null,
      schedule_cron: cron.trim() ? cron.trim() : null,
      config: {
        scraper,
        preprocessor,
        processor,
      },
    });
  }

  function validateStep(currentStep: Step): boolean {
    setError(null);

    if (currentStep === 1) {
      if (!name.trim()) {
        setError("Name is required");
        return false;
      }
      if (!url.trim()) {
        setError("URL is required");
        return false;
      }
      if (carrierId.trim() && Number.isNaN(Number(carrierId))) {
        setError("Carrier id must be a number");
        return false;
      }
      if (cron.trim() && !cronReadable) {
        setError("Cron expression is invalid");
        return false;
      }
    }

    if (currentStep === 3) {
      if (usePreprocessor) {
        for (const tool of tools) {
          if (!tool.ref.trim()) {
            setError("Every preprocessor tool needs a ref");
            return false;
          }
          try {
            parseObjectArray(tool.params);
          } catch (exc) {
            const message = exc instanceof Error ? exc.message : "Invalid tool params JSON";
            setError(message);
            return false;
          }
        }
      }

      if (useProcessor) {
        try {
          parseObject(apiParamsRaw);
        } catch (exc) {
          const message = exc instanceof Error ? exc.message : "Invalid api params JSON";
          setError(message);
          return false;
        }
      }
    }

    return true;
  }

  function nextStep() {
    if (!validateStep(step)) {
      return;
    }

    setStep((current) => Math.min(4, current + 1) as Step);
  }

  function prevStep() {
    setError(null);
    setStep((current) => Math.max(1, current - 1) as Step);
  }

  async function handleCreateTarget() {
    if (!validateStep(step)) {
      return;
    }

    let payload: NewTarget;
    try {
      payload = buildPayload();
    } catch (exc) {
      const message = exc instanceof Error ? exc.message : "Invalid target payload";
      setError(message);
      return;
    }

    setLoading(true);
    try {
      await apiFetch("/targets", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      toast?.success("Target created");
      navigate("/targets");
    } catch (exc) {
      const message = exc instanceof Error ? exc.message : "Failed to create target";
      toast?.error(message);
    } finally {
      setLoading(false);
    }
  }

  const previewPayload = useMemo(() => {
    try {
      return JSON.stringify(buildPayload(), null, 2);
    } catch {
      return "Complete all required fields to preview payload.";
    }
  }, [
    name,
    url,
    isActive,
    carrierId,
    cron,
    scrapeMethod,
    firecrawlFormat,
    scraplingMode,
    scraplingFetcher,
    scraplingForceMime,
    scraplingSelectors,
    scriptPath,
    usePreprocessor,
    tools,
    useProcessor,
    provider,
    systemPrompt,
    userPrompts,
    apiParamsRaw,
  ]);

  useEffect(() => {
    const url = `/scripts/${scrapeMethod === "scrapling" ? "scrapling" : "firecrawl"}?search=${scriptPath}`;
    apiFetch(url, { method: "GET" })
      .then((r) => r.json())
      .then((data) => {
        setScriptsList(data);
      })
  }, [debouncedScriptPath])

  return (
    <Layout>
      <Background />
      <form onSubmit={(e) => e.preventDefault()} className="panel mx-auto flex w-full max-w-6xl flex-col">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight text-white">Add target</h1>
            <p className="mt-1 text-sm text-white/70">Step {step} of 4 — {stepLabels[step]}</p>
          </div>

          <NavLink to="/targets" className="btn-secondary">
            <ArrowLeft size={16} />
            Back to targets
          </NavLink>
        </div>

        <hr className="my-6 border-t border-accent-light/40" />

        <div className="mx-auto mb-6 grid w-full max-w-3xl grid-cols-2 gap-2 sm:grid-cols-4">
          {steps.map((stepNo) => (
            <button
              key={stepNo}
              type="button"
              onClick={() => setStep(stepNo)}
              className={stepNo === step ? "btn-primary justify-center" : "btn-secondary justify-center"}
            >
              {stepNo}. {stepLabels[stepNo]}
            </button>
          ))}
        </div>

        <div className="px-1">
          {step === 1 ? (
            <div className="mx-auto grid w-full max-w-3xl gap-4 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <label htmlFor="name" className="mb-1 block text-sm text-white">Name</label>
                <input id="name" value={name} onChange={(e) => setName(e.target.value)} className="text-input w-full" placeholder="Example: school buses" />
              </div>

              <div className="sm:col-span-2">
                <label htmlFor="url" className="mb-1 block text-sm text-white">URL</label>
                <input id="url" value={url} onChange={(e) => setUrl(e.target.value)} className="text-input w-full" placeholder="https://example.com/timetable" />
              </div>

              <div className="sm:col-span-2 grid items-start gap-4 sm:grid-cols-[minmax(0,1fr)_auto]">
                <div className="min-w-0">
                  <label htmlFor="carrier" className="mb-1 block text-sm text-white">Carrier id (optional)</label>
                  <input id="carrier" value={carrierId} onChange={(e) => setCarrierId(e.target.value)} className="text-input w-full" inputMode="numeric" />
                </div>

                <div>
                  <label className="mb-1 block text-sm text-white">Target active</label>
                  <div className="flex h-10 items-center gap-2">
                    <Switch id="is_active" checked={isActive} onCheckedChange={setIsActive} />
                    <label htmlFor="is_active" className="text-sm text-white">Target is active</label>
                  </div>
                </div>

                <div className="min-w-0">
                  <label htmlFor="cron" className="mb-1 block text-sm text-white">Schedule cron (optional)</label>
                  <div className="flex w-full items-center gap-2">
                    <CalendarClock size={18} className="text-white/70" />
                    <input id="cron" value={cron} onChange={(e) => setCron(e.target.value)} className="text-input w-full" placeholder="0 9 * * *" />
                  </div>
                  {cron.trim() ? (
                    <p className="mt-2 text-sm text-white/70">
                      {cronReadable ? cronReadable : "Invalid cron"}
                    </p>
                  ) : null}
                </div>

                <div>
                  <label className="mb-1 block text-sm text-white">Cron presets</label>
                  <Popover.Root>
                    <Popover.Trigger className="w-full btn-secondary">
                      <WandSparkles size={14} />
                      Presets
                    </Popover.Trigger>
                    <Popover.Portal>
                      <Popover.Positioner sideOffset={8} align="start" className="z-10">
                        <Popover.Popup className="w-44 rounded-xl border border-accent-light/30 bg-surface/95 p-2 shadow-lg backdrop-blur-sm outline-none">
                          <div className="grid gap-1">
                            {cronPresets.map((preset) => (
                              <Popover.Close
                                key={preset.value}
                                onClick={() => setCron(preset.value)}
                                className="btn-secondary w-full justify-start"
                              >
                                {preset.label}
                              </Popover.Close>
                            ))}
                          </div>
                        </Popover.Popup>
                      </Popover.Positioner>
                    </Popover.Portal>
                  </Popover.Root>
                </div>
              </div>
            </div>
          ) : null}

          {step === 2 ? (
            <div className="mx-auto grid w-full max-w-3xl gap-4 sm:grid-cols-3">
              <div>
                <label className="mb-1 block text-sm text-white">Scraper</label>
                <select
                  value={scrapeMethod}
                  onChange={(e) => setScrapeMethod(e.target.value as ScrapeMethod)}
                  className="text-input w-full"
                >
                  <option value="firecrawl">Firecrawl</option>
                  <option value="scrapling">Scrapling</option>
                </select>
              </div>

              {scrapeMethod === "firecrawl" ? (
                <div className="sm:col-span-2">
                  <label htmlFor="firecrawl_format" className="mb-1 block text-sm text-white">Format (optional)</label>
                  <input
                    id="firecrawl_format"
                    className="text-input w-full"
                    value={firecrawlFormat}
                    onChange={(e) => setFirecrawlFormat(e.target.value)}
                    placeholder="markdown"
                  />
                </div>
              ) : (
                <>
                  <div className="sm:col-span-3">
                    <label htmlFor="scrapling_mode" className="mb-1 block text-sm text-white">Mode</label>
                    <select
                      id="scrapling_mode"
                      value={scraplingMode}
                      onChange={(e) => setScraplingMode(e.target.value as ScraplingMode)}
                      className="text-input w-full"
                    >
                      <option value="simple">Simple (fetch + optional selectors)</option>
                      <option value="script">Script (custom Python)</option>
                    </select>
                  </div>

                  {scraplingMode === "simple" ? (
                    <>
                      <div>
                        <label htmlFor="fetcher" className="mb-1 block text-sm text-white">Fetcher</label>
                        <select
                          id="fetcher"
                          value={scraplingFetcher}
                          onChange={(e) => setScraplingFetcher(e.target.value as typeof scraplingFetcher)}
                          className="text-input w-full"
                        >
                          <option value="AsyncFetcher">AsyncFetcher</option>
                          <option value="DynamicFetcher">DynamicFetcher</option>
                          <option value="StealthyFetcher">StealthyFetcher</option>
                        </select>
                      </div>

                      <div>
                        <label htmlFor="force_mime" className="mb-1 block text-sm text-white">Force mime (optional)</label>
                        <input
                          id="force_mime"
                          className="text-input w-full"
                          value={scraplingForceMime}
                          onChange={(e) => setScraplingForceMime(e.target.value)}
                          disabled={!!scraplingSelectors.trim()}
                          placeholder={scraplingSelectors.trim() ? "disabled while selectors are set" : ""}
                        />
                      </div>

                      <div className="sm:col-span-3">
                        <label htmlFor="selectors" className="mb-1 block text-sm text-white">Selectors (one per line, optional)</label>
                        <textarea
                          id="selectors"
                          className="text-input min-h-28 w-full"
                          value={scraplingSelectors}
                          onChange={(e) => setScraplingSelectors(e.target.value)}
                          placeholder="table tr"
                        />
                      </div>
                    </>
                  ) : (
                    <div className="sm:col-span-3">
                      <label htmlFor="script_path" className="mb-1 block text-sm text-white">Script path</label>
                      <Combobox.Root
                        items={scriptsList}
                        inputValue={scriptPath}
                        onInputValueChange={(value) => setScriptPath(value)}
                        value={scriptPath || null}
                        onValueChange={(value) => setScriptPath(value ?? "")}
                        // server-side filtering: bypass internal filter
                        filter={() => true}
                      >
                        <Combobox.Input
                          id="script_path"
                          className="text-input w-full"
                          placeholder="worker/scrapers/scripts/custom.py"
                          autoComplete="off"
                        />
                        <Combobox.Portal>
                          <Combobox.Positioner sideOffset={4} align="start" className="z-10">
                            <Combobox.Popup className="max-h-64 w-[var(--anchor-width)] overflow-auto rounded-xl border border-accent-light/30 bg-surface/95 p-1 shadow-lg backdrop-blur-sm outline-none">
                              <Combobox.Empty className="px-3 py-2 text-sm text-white/60">
                                No scripts found
                              </Combobox.Empty>
                              <Combobox.List>
                                {(script: string) => (
                                  <Combobox.Item
                                    key={script}
                                    value={script}
                                    className="block w-full cursor-pointer rounded-lg px-3 py-2 text-left text-sm text-white/80 data-[highlighted]:bg-white/5 data-[highlighted]:text-white"
                                  >
                                    {script}
                                  </Combobox.Item>
                                )}
                              </Combobox.List>
                            </Combobox.Popup>
                          </Combobox.Positioner>
                        </Combobox.Portal>
                      </Combobox.Root>
                    </div>
                  )}
                </>
              )}
            </div>
          ) : null}

          {step === 3 ? (
            <div className="mx-auto grid w-full max-w-3xl gap-6">
              <section>
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="text-lg text-white">Preprocessor</h2>
                  <div className="flex items-center gap-2">
                    <label htmlFor="use_preprocessor" className="text-sm text-white">Enabled</label>
                    <Switch id="use_preprocessor" checked={usePreprocessor} onCheckedChange={setUsePreprocessor} />
                  </div>
                </div>

                {usePreprocessor ? (
                  <>
                    <div className="grid gap-3">
                      {tools.map((tool, index) => (
                        <div key={tool.id} className="rounded-lg border border-accent-light/20 p-3">
                          <div className="mb-2 flex items-center justify-between">
                            <span className="text-sm text-white/80">Tool #{index + 1}</span>
                            <button type="button" className="btn-secondary" onClick={() => removeTool(tool.id)}>
                              <Trash2 size={14} />
                              Remove
                            </button>
                          </div>

                          <label className="mb-1 block text-sm text-white">Ref</label>
                          <input
                            className="text-input w-full"
                            value={tool.ref}
                            onChange={(e) => updateTool(tool.id, { ref: e.target.value })}
                            placeholder="module:function"
                          />

                          <label className="mb-1 mt-3 block text-sm text-white">Params JSON array (optional)</label>
                          <textarea
                            className="text-input min-h-24 w-full"
                            value={tool.params}
                            onChange={(e) => updateTool(tool.id, { params: e.target.value })}
                            placeholder='[{"threshold": 0.8}]'
                          />
                        </div>
                      ))}

                      {tools.length === 0 ? (
                        <p className="text-sm text-white/60">No tools configured yet.</p>
                      ) : null}
                    </div>

                    <div className="mt-4 flex justify-end">
                      <button type="button" className="btn-secondary" onClick={addTool}>
                        <Plus size={16} />
                        Add tool
                      </button>
                    </div>
                  </>
                ) : (
                  <p className="text-sm text-white/60">Disabled. No preprocessing tools will run.</p>
                )}
              </section>

              <hr className="border-t border-accent-light/40" />

              <section>
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="text-lg text-white">Processor (LLM)</h2>
                  <div className="flex items-center gap-2">
                    <label htmlFor="use_processor" className="text-sm text-white">Enabled</label>
                    <Switch id="use_processor" checked={useProcessor} onCheckedChange={setUseProcessor} />
                  </div>
                </div>

                {useProcessor ? (
                  <div className="grid gap-4">
                    <div className="flex items-end gap-3">
                      <div className="shrink-0">
                        <label className="mb-1 block text-sm text-white">Provider</label>
                        <select className="text-input" value={provider} onChange={(e) => setProvider(e.target.value as LlmProvider)}>
                          <option value="openrouter">openrouter</option>
                          <option value="gemini">gemini</option>
                        </select>
                      </div>

                      <div className="flex-1 min-w-0">
                        <label className="mb-1 block text-sm text-white">Model</label>
                        <input className="text-input w-full" value="gemini-3-flash-preview" disabled />
                      </div>
                    </div>

                    <div>
                      <label className="mb-1 block text-sm text-white">System prompt (optional)</label>
                      <textarea className="text-input min-h-24 w-full" value={systemPrompt} onChange={(e) => setSystemPrompt(e.target.value)} />
                    </div>

                    <div>
                      <label className="mb-1 block text-sm text-white">User prompts (one per line)</label>
                      <textarea className="text-input min-h-24 w-full" value={userPrompts} onChange={(e) => setUserPrompts(e.target.value)} />
                    </div>

                    <div>
                      <label className="mb-1 block text-sm text-white">API params JSON object (optional)</label>
                      <textarea className="text-input min-h-24 w-full" value={apiParamsRaw} onChange={(e) => setApiParamsRaw(e.target.value)} placeholder='{"temperature": 0.2}' />
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-white/60">Disabled. No processing step will run.</p>
                )}
              </section>
            </div>
          ) : null}

          {step === 4 ? (
            <div className="mx-auto w-full max-w-3xl">
              <p className="mb-3 text-sm text-white/70">Review the payload before creating the target.</p>
              <pre className="max-h-[26rem] overflow-auto rounded-xl border border-accent-light/30 bg-black/30 p-4 text-xs text-white/90">
                {previewPayload}
              </pre>
            </div>
          ) : null}
        </div>

        {error ? (
          <p className="mt-4 text-sm text-red-300">{error}</p>
        ) : null}

        <div className="mt-6 flex items-center justify-between gap-3">
          <button type="button" className="btn-secondary" onClick={prevStep} disabled={step === 1 || loading}>
            <ArrowLeft size={16} />
            Previous
          </button>

          {step < 4 ? (
            <button type="button" className="btn-primary" onClick={nextStep} disabled={loading}>
              Next
            </button>
          ) : (
            <button type="button" className="btn-primary" onClick={() => void handleCreateTarget()} disabled={loading}>
              {loading ? <Loader2 size={18} className="animate-spin" /> : "Create target"}
            </button>
          )}
        </div>
      </form>
    </Layout>
  );
}
