import SectionMessage from "./SectionMessage";
import Spinner from "./Spinner";
import EmptyState from "./EmptyState";

type EmptyConfig = {
  title: string;
  description?: string;
  action?: React.ReactNode;
};

type Props = {
  title: string;
  subtitle?: string;
  error?: string;
  loading?: boolean;
  loadingLabel?: string;
  empty?: EmptyConfig | null;
  actions?: React.ReactNode;
  breadcrumbs?: React.ReactNode;
  children?: React.ReactNode;
};

export default function PageLayout({
  title,
  subtitle,
  error,
  loading,
  loadingLabel = "Loading…",
  empty,
  actions,
  breadcrumbs,
  children,
}: Props) {
  return (
    <section>
      {breadcrumbs}
      <div className="page-layout-header">
        <div className="page-layout-heading">
          <h1 className="page-title">{title}</h1>
          {subtitle && <p className="page-subtitle">{subtitle}</p>}
        </div>
        {actions && <div className="page-layout-actions">{actions}</div>}
      </div>

      <SectionMessage appearance="error">{error ?? ""}</SectionMessage>

      {loading && <Spinner label={loadingLabel} />}

      {!loading && empty && (
        <EmptyState
          title={empty.title}
          description={empty.description}
          action={empty.action}
        />
      )}

      {!loading && !empty && children}
    </section>
  );
}
