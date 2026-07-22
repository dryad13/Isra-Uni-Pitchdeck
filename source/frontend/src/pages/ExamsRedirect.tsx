import { Navigate } from "react-router-dom";

export default function ExamsRedirect() {
  return <Navigate to="/?view=manage" replace />;
}
