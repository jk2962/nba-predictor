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
        <div className="card" style={{ padding: 'var(--space-lg)' }}>
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: 'var(--space-lg)',
            }}>
                <h3 style={{
                    fontSize: '1.125rem',
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                    letterSpacing: '-0.01em',
                }}>
                    Next Game Prediction
                </h3>
                {prediction.opponent_team && (
                    <span style={{
                        fontSize: '0.8125rem',
                        color: 'var(--text-tertiary)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.02em',
                    }}>
                        vs {prediction.opponent_team} {prediction.is_home ? '(Home)' : '(Away)'}
                    </span>
                )}
            </div>

            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: 'var(--space-md)',
            }}>
                <PredictionStat
                    label="Points"
                    value={prediction.predicted_points}
                    lower={prediction.points_lower}
                    upper={prediction.points_upper}
                    showConfidence={showConfidence}
                />
                <PredictionStat
                    label="Rebounds"
                    value={prediction.predicted_rebounds}
                    lower={prediction.rebounds_lower}
                    upper={prediction.rebounds_upper}
                    showConfidence={showConfidence}
                />
                <PredictionStat
                    label="Assists"
                    value={prediction.predicted_assists}
                    lower={prediction.assists_lower}
                    upper={prediction.assists_upper}
                    showConfidence={showConfidence}
                />
            </div>

            {prediction.fantasy_score && (
                <div style={{
                    marginTop: 'var(--space-lg)',
                    paddingTop: 'var(--space-lg)',
                    borderTop: '1px solid var(--border-subtle)',
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'baseline',
                    gap: 'var(--space-sm)',
                }}>
                    <div className="data-label">
                        Projected Fantasy
                    </div>
                    <div className="data-primary" style={{
                        color: 'var(--hot)',
                    }}>
                        {prediction.fantasy_score.toFixed(1)}
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
    showConfidence,
}: {
    label: string;
    value: number;
    lower: number;
    upper: number;
    showConfidence: boolean;
}) {
    // Calculate confidence width based on range relative to value
    const range = upper - lower;
    const confidenceWidth = Math.max(20, Math.min(100, 100 - (range / value) * 50));

    return (
        <div style={{
            background: 'var(--surface-1)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-md)',
            padding: 'var(--space-md)',
            textAlign: 'center',
        }}>
            <div className="data-label" style={{
                marginBottom: 'var(--space-sm)',
            }}>
                {label}
            </div>

            <div className="data-primary" style={{
                color: 'var(--hot)',
                marginBottom: 'var(--space-sm)',
            }}>
                {value.toFixed(1)}
            </div>

            {showConfidence && (
                <>
                    <div style={{
                        fontSize: '0.75rem',
                        color: 'var(--text-tertiary)',
                        marginBottom: 'var(--space-sm)',
                        fontVariantNumeric: 'tabular-nums',
                    }}>
                        {lower.toFixed(1)} - {upper.toFixed(1)}
                    </div>

                    <div className="confidence-bar">
                        <div
                            className="confidence-bar-fill"
                            style={{
                                width: `${confidenceWidth}%`,
                            }}
                        />
                    </div>
                    <div style={{
                        fontSize: '0.6875rem',
                        color: 'var(--text-muted)',
                        marginTop: 'var(--space-xs)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.02em',
                    }}>
                        95% Confidence
                    </div>
                </>
            )}
        </div>
    );
}
