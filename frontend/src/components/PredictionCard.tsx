/**
 * Prediction Card Component
 */
import type { PredictionResult } from '../types';

interface PredictionCardProps {
    prediction: PredictionResult;
    showConfidence?: boolean;
}

export default function PredictionCard({
    prediction,
    showConfidence = true
}: PredictionCardProps) {
    return (
        <div className="card" style={{ padding: '1.5rem' }}>
            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                marginBottom: '1.25rem',
            }}>
                <span style={{ fontSize: '1.5rem' }}>🔮</span>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>
                    Next Game Prediction
                </h3>
                {prediction.opponent_team && (
                    <span style={{
                        marginLeft: 'auto',
                        fontSize: '0.875rem',
                        color: 'var(--color-text-secondary)',
                    }}>
                        vs {prediction.opponent_team} {prediction.is_home ? '(Home)' : '(Away)'}
                    </span>
                )}
            </div>

            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: '1rem',
            }}>
                <PredictionStat
                    label="Points"
                    value={prediction.predicted_points}
                    lower={prediction.points_lower}
                    upper={prediction.points_upper}
                    color="#6366f1"
                    showConfidence={showConfidence}
                />
                <PredictionStat
                    label="Rebounds"
                    value={prediction.predicted_rebounds}
                    lower={prediction.rebounds_lower}
                    upper={prediction.rebounds_upper}
                    color="#22c55e"
                    showConfidence={showConfidence}
                />
                <PredictionStat
                    label="Assists"
                    value={prediction.predicted_assists}
                    lower={prediction.assists_lower}
                    upper={prediction.assists_upper}
                    color="#f97316"
                    showConfidence={showConfidence}
                />
            </div>

            {prediction.fantasy_score && (
                <div style={{
                    marginTop: '1.25rem',
                    paddingTop: '1.25rem',
                    borderTop: '1px solid rgba(255,255,255,0.1)',
                    display: 'flex',
                    justifyContent: 'center',
                }}>
                    <div style={{
                        background: 'var(--gradient-primary)',
                        padding: '0.75rem 2rem',
                        borderRadius: '2rem',
                        textAlign: 'center',
                    }}>
                        <div style={{
                            fontSize: '0.7rem',
                            textTransform: 'uppercase',
                            letterSpacing: '0.1em',
                            color: 'rgba(255,255,255,0.8)',
                            marginBottom: '0.25rem',
                        }}>
                            Projected Fantasy
                        </div>
                        <div style={{
                            fontSize: '1.5rem',
                            fontWeight: 700,
                            color: 'white',
                        }}>
                            {prediction.fantasy_score.toFixed(1)}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

function PredictionStat({
    label,
    value,
    lower,
    upper,
    color,
    showConfidence,
}: {
    label: string;
    value: number;
    lower: number;
    upper: number;
    color: string;
    showConfidence: boolean;
}) {
    // Calculate confidence width based on range relative to value
    const range = upper - lower;
    const confidenceWidth = Math.max(20, Math.min(100, 100 - (range / value) * 50));

    return (
        <div style={{
            background: 'rgba(0,0,0,0.2)',
            borderRadius: '0.75rem',
            padding: '1rem',
            textAlign: 'center',
        }}>
            <div style={{
                fontSize: '0.8rem',
                color: 'var(--color-text-secondary)',
                marginBottom: '0.5rem',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
            }}>
                {label}
            </div>

            <div style={{
                fontSize: '2rem',
                fontWeight: 700,
                color,
                marginBottom: '0.5rem',
            }}>
                {value.toFixed(1)}
            </div>

            {showConfidence && (
                <>
                    <div style={{
                        fontSize: '0.75rem',
                        color: 'var(--color-text-muted)',
                        marginBottom: '0.5rem',
                    }}>
                        {lower.toFixed(1)} - {upper.toFixed(1)}
                    </div>

                    <div className="confidence-bar">
                        <div
                            className="confidence-bar-fill"
                            style={{
                                width: `${confidenceWidth}%`,
                                background: `linear-gradient(90deg, ${color}88, ${color})`,
                            }}
                        />
                    </div>
                    <div style={{
                        fontSize: '0.65rem',
                        color: 'var(--color-text-muted)',
                        marginTop: '0.25rem',
                    }}>
                        95% Confidence
                    </div>
                </>
            )}
        </div>
    );
}
