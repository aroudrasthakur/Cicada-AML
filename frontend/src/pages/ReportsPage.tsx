import { Download, FileText } from "lucide-react";

export default function ReportsPage() {
  const reports: {
    id: string;
    title: string;
    caseName: string;
    generatedAt: string;
  }[] = [];

  return (
    <div className="px-8 py-6 space-y-6">
      <h1 className="text-2xl font-bold text-white">Investigation Reports</h1>

      <div className="rounded-xl bg-gray-900 border border-gray-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-gray-400 border-b border-gray-800 bg-gray-950/40">
                <th className="px-4 py-3 font-medium">Report Title</th>
                <th className="px-4 py-3 font-medium">Case</th>
                <th className="px-4 py-3 font-medium">Generated At</th>
                <th className="px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800 text-gray-300">
              {reports.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-16 text-center">
                    <FileText
                      className="h-10 w-10 text-gray-600 mx-auto mb-3"
                      aria-hidden
                    />
                    <p className="text-gray-400 font-medium">
                      No reports generated
                    </p>
                    <p className="text-gray-500 text-sm mt-2 max-w-sm mx-auto">
                      Export or generate investigation reports to list them
                      here.
                    </p>
                  </td>
                </tr>
              ) : (
                reports.map((r) => (
                  <tr key={r.id} className="hover:bg-gray-800/40">
                    <td className="px-4 py-3 text-white font-medium">
                      {r.title}
                    </td>
                    <td className="px-4 py-3">{r.caseName}</td>
                    <td className="px-4 py-3 text-gray-400">{r.generatedAt}</td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        className="inline-flex items-center gap-1.5 rounded-lg border border-gray-700 bg-gray-800 px-3 py-1.5 text-xs font-medium text-gray-200 hover:bg-gray-700 hover:border-gray-600 transition-colors"
                      >
                        <Download className="h-3.5 w-3.5" aria-hidden />
                        Download
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
