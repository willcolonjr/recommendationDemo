import { ChangeEvent, FormEvent, useMemo } from "react";

import { EmbeddingModelOption } from "../types";

export interface PreferenceFormState {
  destination: string;
  travelSeason: string;
  travelStyle: string;
  groupType: string;
  mustHaveAmenities: string;
  budget: string;
  extraNotes: string;
}

interface PreferenceFormProps {
  value: PreferenceFormState;
  submitting: boolean;
  onChange: (next: PreferenceFormState) => void;
  onSubmit: () => void;
  modelOptions: EmbeddingModelOption[];
  selectedModelId: string | null;
  onModelChange: (modelId: string) => void;
  modelError?: string | null;
}

const PreferenceForm = ({
  value,
  submitting,
  onChange,
  onSubmit,
  modelOptions,
  selectedModelId,
  onModelChange,
  modelError,
}: PreferenceFormProps) => {
  const handleChange = (event: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value: fieldValue } = event.target;
    onChange({ ...value, [name]: fieldValue });
  };

  const handleModelChange = (event: ChangeEvent<HTMLSelectElement>) => {
    onModelChange(event.target.value);
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit();
  };

  const selectedModel = useMemo(
    () => modelOptions.find((option) => option.id === selectedModelId) ?? null,
    [modelOptions, selectedModelId]
  );

  const modelPlaceholder = modelError ? "Models unavailable" : "Loading models…";
  const modelsAvailable = modelOptions.length > 0;

  return (
    <form className="form" onSubmit={handleSubmit}>
      <div className="form__grid">
        <label className="field">
          <span className="field__label">Preferred destination or region</span>
          <input
            name="destination"
            value={value.destination}
            onChange={handleChange}
            placeholder="e.g. Caribbean, mountains"
          />
        </label>

        <label className="field">
          <span className="field__label">Travel season</span>
          <input
            name="travelSeason"
            value={value.travelSeason}
            onChange={handleChange}
            placeholder="e.g. summer, winter holidays"
          />
        </label>

        <label className="field">
          <span className="field__label">Travel style</span>
          <select name="travelStyle" value={value.travelStyle} onChange={handleChange}>
            <option value="relaxation">Relaxation &amp; spa</option>
            <option value="adventure">Adventure &amp; excursions</option>
            <option value="family friendly">Family friendly</option>
            <option value="romantic">Romantic escape</option>
            <option value="nightlife">Nightlife &amp; entertainment</option>
          </select>
        </label>

        <label className="field">
          <span className="field__label">Who&apos;s traveling?</span>
          <select name="groupType" value={value.groupType} onChange={handleChange}>
            <option value="family">Family with kids</option>
            <option value="couple">Couple</option>
            <option value="friends">Friends trip</option>
            <option value="solo">Solo traveler</option>
          </select>
        </label>

        <label className="field field--wide">
          <span className="field__label">Must-have amenities</span>
          <input
            name="mustHaveAmenities"
            value={value.mustHaveAmenities}
            onChange={handleChange}
            placeholder="Water park, golf course, beachfront..."
          />
        </label>

        <label className="field">
          <span className="field__label">Budget notes</span>
          <input
            name="budget"
            value={value.budget}
            onChange={handleChange}
            placeholder="e.g. mid-range, luxury"
          />
        </label>
      </div>

      <label className="field">
        <span className="field__label">Anything else we should know?</span>
        <textarea
          name="extraNotes"
          value={value.extraNotes}
          onChange={handleChange}
          rows={3}
          placeholder="Accessibility needs, room requirements, activities..."
        />
      </label>

      <label className="field">
        <span className="field__label">Embedding model</span>
        <select
          name="embeddingModel"
          value={selectedModelId ?? ""}
          onChange={handleModelChange}
          disabled={!modelsAvailable}
        >
          {!modelsAvailable ? (
            <option value="">{modelPlaceholder}</option>
          ) : (
            modelOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.name} · {option.provider}
              </option>
            ))
          )}
        </select>
        <p className="field__hint">Swap between available embeddings used by the vector search pipeline.</p>
        {selectedModel && (
          <p className="field__hint field__hint--muted">{selectedModel.description}</p>
        )}
        {modelError && <p className="field__hint field__hint--error">{modelError}</p>}
      </label>

      <div className="form__actions">
        <button type="submit" className="button" disabled={submitting}>
          {submitting ? "Finding resorts..." : "Find resorts"}
        </button>
      </div>
    </form>
  );
};

export default PreferenceForm;
