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
                padding: 'var(--space-2xl)',
                gap: 'var(--space-lg)',
            }}
        >
            <Spinner size="lg" />
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9375rem' }}>{message}</p>
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
                padding: 'var(--space-2xl)',
                gap: 'var(--space-md)',
                textAlign: 'center',
                borderColor: 'var(--error)',
            }}
        >
            <div style={{
                width: '48px',
                height: '48px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--surface-3)',
                border: '2px solid var(--error)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '1.5rem',
                fontWeight: 700,
                color: 'var(--error)',
            }}>
                !
            </div>
            <h3 style={{ color: 'var(--error)', fontSize: '1.125rem' }}>Error</h3>
            <p style={{ color: 'var(--text-secondary)', maxWidth: '400px', fontSize: '0.9375rem' }}>
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
}: {
    title?: string;
    description?: string;
}) {
    return (
        <div
            style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                padding: 'var(--space-2xl)',
                gap: 'var(--space-md)',
                textAlign: 'center',
            }}
        >
            <div style={{
                width: '64px',
                height: '64px',
                borderRadius: 'var(--radius-lg)',
                background: 'var(--surface-2)',
                border: '1px solid var(--border)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
            }}>
                <div style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    border: '3px solid var(--border-emphasis)',
                    borderTopColor: 'transparent',
                }} />
            </div>
            <h3 style={{ color: 'var(--text-primary)', fontSize: '1.125rem' }}>{title}</h3>
            <p style={{ color: 'var(--text-secondary)', maxWidth: '400px', fontSize: '0.9375rem' }}>
                {description}
            </p>
        </div>
    );
}

export default { Spinner, LoadingState, ErrorState, EmptyState };
