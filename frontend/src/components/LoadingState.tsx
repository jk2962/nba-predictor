/**
 * Loading Spinner Component
 */
export function Spinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
    const sizeMap = {
        sm: '24px',
        md: '40px',
        lg: '60px',
    };

    return (
        <div
            className="spinner"
            style={{
                width: sizeMap[size],
                height: sizeMap[size],
            }}
        />
    );
}

/**
 * Loading State Component
 */
export function LoadingState({ message = 'Loading...' }: { message?: string }) {
    return (
        <div
            style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '4rem 2rem',
                gap: '1.5rem',
            }}
        >
            <Spinner size="lg" />
            <p style={{ color: 'var(--color-text-secondary)' }}>{message}</p>
        </div>
    );
}

/**
 * Error State Component
 */
export function ErrorState({
    message = 'Something went wrong',
    onRetry,
}: {
    message?: string;
    onRetry?: () => void;
}) {
    return (
        <div
            className="card"
            style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '3rem 2rem',
                gap: '1rem',
                textAlign: 'center',
                borderColor: 'rgba(239, 68, 68, 0.3)',
            }}
        >
            <span style={{ fontSize: '3rem' }}>⚠️</span>
            <h3 style={{ color: 'var(--color-error)' }}>Error</h3>
            <p style={{ color: 'var(--color-text-secondary)', maxWidth: '400px' }}>
                {message}
            </p>
            {onRetry && (
                <button className="btn btn-secondary" onClick={onRetry}>
                    Try Again
                </button>
            )}
        </div>
    );
}

/**
 * Empty State Component
 */
export function EmptyState({
    title = 'No data found',
    description = 'Try adjusting your search or filters.',
    icon = '🔍',
}: {
    title?: string;
    description?: string;
    icon?: string;
}) {
    return (
        <div
            style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '4rem 2rem',
                gap: '1rem',
                textAlign: 'center',
            }}
        >
            <span style={{ fontSize: '3rem', opacity: 0.5 }}>{icon}</span>
            <h3 style={{ color: 'var(--color-text-primary)' }}>{title}</h3>
            <p style={{ color: 'var(--color-text-secondary)', maxWidth: '400px' }}>
                {description}
            </p>
        </div>
    );
}

export default { Spinner, LoadingState, ErrorState, EmptyState };
