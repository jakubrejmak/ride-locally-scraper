import { type SubmitEvent, useState, useMemo } from "react";
import { NavLink } from "react-router-dom";
import { ArrowLeft, CalendarClock, Loader2, Plus, Trash2, WandSparkles } from "lucide-react";
import Layout from "../../components/Layout/Layout";
import Background from "../../components/Background/Background";
import { z } from "zod"
import cronstrue from "cronstrue"

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

const scraplingConfigSchema = z.object({
  scrape_method: z.literal("scrapling"),
  force_mime: z.string().nullable().optional(),
  fetcher: scraplingFetcherSchema.optional(),
  selectors: z.array(z.string()).nullable().optional(),
  script_path: z.string().nullable().optional(),
});

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

type NewTarget = z.infer<typeof newTargetSchema>;
export type Target = NewTarget & { id: number; }
type ScrTargetConfig = z.infer<typeof scrTargetConfigSchema>;
type ScraperConfig = z.infer<typeof scraperConfigSchema>;
type FirecrawlConfig = z.infer<typeof firecrawlConfigSchema>;
type ScraplingConfig = z.infer<typeof scraplingConfigSchema>;
type PreprocessorTool = z.infer<typeof preprocessorToolSchema>;

export default function AddTarget(): React.ReactNode {
  const [loading, setLoading] = useState<boolean>(false);
  const [tools, setTools] = useState<PreprocessorTool[]>([])
  const [cron, setCron] = useState<string>("");

  function handleSubmit(e: SubmitEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);

    const form = e.currentTarget;
    const data = new FormData(form);
  }

  function addTool(tool: PreprocessorTool) {
    setTools([...tools, tool])
  }

  const cronReadable = useMemo<string>(() => {
    try {
      return cronstrue.toString(cron);
    } catch (exc) {
      return;
    }
  }, [cron])

  return (
    <Layout>
    </Layout>
  );
}
