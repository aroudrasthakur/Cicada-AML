import { GitBranch, Info, SlidersHorizontal } from "lucide-react";

export default function FlowExplorerPage() {
  return (
    <div className="px-8 py-6 flex flex-col h-full min-h-[calc(100vh-0px)]">
      <h1 className="text-2xl font-bold text-white mb-6">Flow Explorer</h1>

      <div className="flex flex-1 flex-col lg:flex-row gap-4 min-h-0">
        <div className="flex-1 flex flex-col gap-4 min-h-0">
          <div className="flex-1 min-h-[280px] rounded-xl bg-gray-900 border border-gray-800 p-6 flex flex-col">
            <div className="flex items-center gap-2 mb-4">
              <GitBranch className="h-5 w-5 text-blue-400" aria-hidden />
              <h2 className="text-sm font-semibold text-gray-300">
                Fund flow graph
              </h2>
            </div>
            <div className="flex-1 rounded-lg border-2 border-dashed border-gray-700 bg-gray-950/60 flex items-center justify-center text-center px-8">
              <p className="text-gray-500 text-sm max-w-md">
                Select a wallet or transaction to explore fund flows
              </p>
            </div>
          </div>

          <div className="rounded-xl bg-gray-900 border border-gray-800 p-6">
            <div className="flex items-center gap-2 mb-4">
              <SlidersHorizontal
                className="h-4 w-4 text-gray-400"
                aria-hidden
              />
              <span className="text-sm font-medium text-gray-300">
                Time range
              </span>
            </div>
            <div className="h-2 rounded-full bg-gray-800 overflow-hidden">
              <div
                className="h-full w-1/3 rounded-full bg-blue-600/50"
                aria-hidden
              />
            </div>
            <div className="flex justify-between text-xs text-gray-500 mt-2">
              <span>Start</span>
              <span>End (placeholder)</span>
            </div>
          </div>
        </div>

        <aside className="w-full lg:w-80 shrink-0 rounded-xl bg-gray-900 border border-gray-800 p-6 flex flex-col">
          <div className="flex items-center gap-2 mb-4">
            <Info className="h-4 w-4 text-gray-400" aria-hidden />
            <h2 className="text-sm font-semibold text-gray-300">
              Node details
            </h2>
          </div>
          <p className="text-sm text-gray-500 leading-relaxed">
            Click a node in the graph to inspect address, volume, risk signals,
            and connected flows. Nothing selected.
          </p>
        </aside>
      </div>
    </div>
  );
}
