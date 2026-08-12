"use client";

import { Header } from "@/components/Header";
import { Button } from "@/components/ui/Button";
import { ResultsView } from "@/components/results/ResultsView";
import { ScanningView } from "@/components/scan/ScanningView";
import { UploadView } from "@/components/upload/UploadView";
import { useAnalysis } from "@/hooks/useAnalysis";

/**
 * Top-level client controller. Drives the flow state machine and swaps between
 * the three views (Upload → Scanning → Results). Keeping the report in memory
 * avoids serializing a large object through the router.
 */
export function Dashboard() {
  const analysis = useAnalysis();
  const { status, report } = analysis;

  const isScanning = status === "ingesting" || status === "analyzing";
  const isDone = status === "done" && report !== null;
  const isLanding = !isScanning && !isDone;

  return (
    <div className="min-h-screen">
      {/* On the landing the big centered wordmark is the header, so the slim
          nav only shows once you're scanning or viewing results. */}
      {!isLanding && (
        <Header
          action={
            isDone ? (
              <Button variant="ghost" size="sm" onClick={analysis.reset}>
                New scan
              </Button>
            ) : undefined
          }
        />
      )}

      <main>
        {isScanning ? (
          <ScanningView status={status as "ingesting" | "analyzing"} />
        ) : isDone ? (
          <ResultsView report={report} />
        ) : (
          <UploadView
            onUploadFile={analysis.analyzeFromFile}
            onSubmitUrl={analysis.analyzeFromGithub}
            error={analysis.error}
          />
        )}
      </main>
    </div>
  );
}
