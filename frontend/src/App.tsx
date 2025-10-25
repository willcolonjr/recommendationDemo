import { useEffect, useMemo, useState } from "react";
import PreferenceForm, { PreferenceFormState } from "./components/PreferenceForm";
import RecommendationList from "./components/RecommendationList";
import { EmbeddingModelListResponse, EmbeddingModelOption, Recommendation } from "./types";

const DEFAULT_STATE: PreferenceFormState = {
  destination: "",
  travelSeason: "",
  travelStyle: "relaxation",
  groupType: "family",
  mustHaveAmenities: "",
  budget: "",
  extraNotes: ""
};

const App = () => {
  const [formState, setFormState] = useState<PreferenceFormState>(DEFAULT_STATE);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [modelOptions, setModelOptions] = useState<EmbeddingModelOption[]>([]);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [modelError, setModelError] = useState<string | null>(null);

  const query = useMemo(() => {
    const parts = (
      [
        formState.travelStyle,
        formState.groupType,
        formState.destination,
        formState.travelSeason && `${formState.travelSeason} trip`,
        formState.mustHaveAmenities && `amenities: ${formState.mustHaveAmenities}`,
        formState.budget && `budget ${formState.budget}`,
        formState.extraNotes
      ].filter(Boolean) as string[]
    );

    return queryFromParts(parts);
  }, [formState]);

  const handleChange = (state: PreferenceFormState) => {
    setFormState(state);
  };

  useEffect(() => {
    let active = true;

    const loadModels = async () => {
      try {
        const response = await fetch("/api/models");
        if (!response.ok) {
          const payload = await response.json().catch(() => ({}));
          throw new Error(payload.detail ?? "Unable to load embedding models.");
        }

        const data = (await response.json()) as EmbeddingModelListResponse;
        if (!active) {
          return;
        }

        setModelOptions(data.models);
        const defaultId = data.default_model_id || data.models[0]?.id || null;
        setSelectedModel(defaultId);
        setModelError(null);
      } catch (err) {
        if (!active) {
          return;
        }
        setModelOptions([]);
        setSelectedModel(null);
        setModelError(err instanceof Error ? err.message : "Unable to load embedding models.");
      }
    };

    loadModels();

    return () => {
      active = false;
    };
  }, []);

  const handleSubmit = async () => {
    if (!query.trim()) {
      setError("Please provide at least one preference to search.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const requestPayload: Record<string, unknown> = {
        query,
        k: 5,
        use_vector: true,
      };

      if (selectedModel) {
        requestPayload.model_id = selectedModel;
      }

      const response = await fetch("/api/recommendations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestPayload)
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail ?? "Unable to fetch recommendations.");
      }

      const data = (await response.json()) as { results: Recommendation[] };
      setRecommendations(data.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
      setRecommendations([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <header className="page__header">
        <h1>Timeshare Resort Recommender</h1>
        <p>
          Describe the getaway you have in mind and we&apos;ll match it with the best
          resorts in the catalog.
        </p>
      </header>

      <main className="page__content">
        <section className="panel">
          <PreferenceForm
            value={formState}
            onChange={handleChange}
            onSubmit={handleSubmit}
            submitting={loading}
            modelOptions={modelOptions}
            selectedModelId={selectedModel}
            onModelChange={(modelId) => setSelectedModel(modelId || null)}
            modelError={modelError}
          />
          <aside className="query-preview">
            <h2>Search prompt</h2>
            <p>{query || "Add details to build an AI search prompt."}</p>
          </aside>
        </section>

        <section className="panel">
          <div className="panel__header">
            <h2>Recommendations</h2>
            {loading && <span className="status status--loading">Loading…</span>}
            {error && <span className="status status--error">{error}</span>}
          </div>
          <RecommendationList recommendations={recommendations} />
        </section>
      </main>
    </div>
  );
};

export default App;

function queryFromParts(parts: string[]): string {
  if (parts.length === 0) {
    return "";
  }

  return `Looking for a ${parts.join(", ")}`;
}
