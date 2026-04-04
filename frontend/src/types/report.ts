export interface Report {
  id: string;
  case_id: string;
  title: string;
  report_path: string | null;
  generated_at: string;
}
