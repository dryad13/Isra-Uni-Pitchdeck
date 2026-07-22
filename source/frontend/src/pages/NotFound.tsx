import { Link } from "react-router-dom";
import PageLayout from "../components/PageLayout";
import Button from "../components/Button";

export default function NotFound() {
  return (
    <PageLayout title="Page not found">
      <div className="not-found panel">
        <h1 aria-hidden="true">404</h1>
        <p className="page-subtitle">
          This page does not exist or may have moved.
        </p>
        <Link to="/">
          <Button variant="primary">Go to Run exam</Button>
        </Link>
      </div>
    </PageLayout>
  );
}
