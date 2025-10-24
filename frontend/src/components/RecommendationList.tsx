import { Recommendation } from "../types";

interface RecommendationListProps {
  recommendations: Recommendation[];
}

const RecommendationList = ({ recommendations }: RecommendationListProps) => {
  if (recommendations.length === 0) {
    return <p className="empty-state">No recommendations yet. Submit the form to get started.</p>;
  }

  return (
    <ul className="recommendations">
      {recommendations.map((recommendation) => (
        <li key={recommendation.id} className="recommendation">
          <div className="recommendation__header">
            <h3>{recommendation.name}</h3>
            <div className="recommendation__metrics">
              <span className="recommendation__score" title="Raw similarity score">
                Score: {recommendation.score.toFixed(3)}
              </span>
              <span className="recommendation__weight" title="Relative weight within this result set">
                Weight: {(recommendation.weight * 100).toFixed(1)}%
              </span>
            </div>
          </div>
          <p className="recommendation__location">{recommendation.location}</p>
          <p>{recommendation.description}</p>
          <p className="recommendation__info">
            <strong>{formatStrategy(recommendation.strategy)}.</strong> {recommendation.info}
          </p>
        </li>
      ))}
    </ul>
  );
};

function formatStrategy(strategy: string): string {
  switch (strategy) {
    case "vector_similarity":
      return "Vector similarity search";
    case "text_similarity":
      return "Text similarity search";
    default:
      return strategy;
  }
}

export default RecommendationList;
