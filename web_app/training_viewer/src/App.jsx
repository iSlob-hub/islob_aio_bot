import React, { useEffect, useMemo, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import { TransformComponent, TransformWrapper } from "react-zoom-pan-pinch";
import "react-pdf/dist/esm/Page/AnnotationLayer.css";
import "react-pdf/dist/esm/Page/TextLayer.css";

const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

const getViewerConfig = () => {
  const config = window.__TRAINING_VIEWER__ || {};
  const basePath = window.location.pathname.replace(/\/$/, "");
  const fallbackUrl = `${window.location.origin}${basePath}/raw`;
  return {
    pdfUrl: config.pdfUrl || fallbackUrl,
    filename: config.filename || ""
  };
};

pdfjs.GlobalWorkerOptions.workerSrc =
  `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

export default function App() {
  const containerRef = useRef(null);
  const pageRefs = useRef([]);
  const observerRef = useRef(null);

  const [{ pdfUrl }] = useState(getViewerConfig);
  const [numPages, setNumPages] = useState(0);
  const [pageWidth, setPageWidth] = useState(760);
  const [status, setStatus] = useState("loading");
  const [currentPage, setCurrentPage] = useState(1);
  const [pageInput, setPageInput] = useState("1");
  const [isEditing, setIsEditing] = useState(false);

  const isIOS = useMemo(
    () => /iP(ad|hone|od)/.test(navigator.userAgent || ""),
    []
  );

  useEffect(() => {
    const updateWidth = () => {
      if (!containerRef.current) return;
      const viewportWidth = window.visualViewport
        ? window.visualViewport.width
        : window.innerWidth;
      const containerWidth = containerRef.current.clientWidth;
      const available = Math.min(containerWidth, viewportWidth);
      const gutter = available < 520 ? 16 : 32;
      const nextWidth = available - gutter;
      setPageWidth(clamp(nextWidth, 280, 1200));
    };

    updateWidth();
    window.addEventListener("resize", updateWidth);
    return () => window.removeEventListener("resize", updateWidth);
  }, []);

  useEffect(() => {
    if (!numPages || !containerRef.current) return;
    if (observerRef.current) {
      observerRef.current.disconnect();
    }

    observerRef.current = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const pageNum = Number(entry.target.dataset.pageNum);
            if (!Number.isNaN(pageNum)) {
              setCurrentPage(pageNum);
            }
          }
        });
      },
      { root: containerRef.current, threshold: 0.5 }
    );

    pageRefs.current.forEach((node) => {
      if (node) observerRef.current.observe(node);
    });

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, [numPages]);

  useEffect(() => {
    if (!isEditing) {
      setPageInput(String(currentPage));
    }
  }, [currentPage, isEditing]);

  const scrollToPage = (pageNum) => {
    const target = pageRefs.current[pageNum - 1];
    if (target) {
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  const onPageInputCommit = () => {
    if (!numPages) return;
    const value = parseInt(pageInput, 10);
    if (Number.isNaN(value)) {
      setPageInput(String(currentPage));
      return;
    }
    const safeValue = clamp(value, 1, numPages);
    setPageInput(String(safeValue));
    scrollToPage(safeValue);
  };

  const pages = Array.from({ length: numPages }, (_, index) => {
    const pageNum = index + 1;
    return (
      <div
        key={`page_${pageNum}`}
        className="page-shell"
        data-page-num={pageNum}
        ref={(node) => {
          pageRefs.current[index] = node;
        }}
      >
        <Page
          pageNumber={pageNum}
          width={pageWidth}
          renderTextLayer
          renderAnnotationLayer
        />
      </div>
    );
  });

  return (
    <div className="app">
      <main className="viewer viewer-full">
        <section className="viewer-shell">
          <div className="pdf-container" ref={containerRef}>
            <TransformWrapper
              minScale={0.8}
              maxScale={3}
              centerOnInit
              doubleClick={{ disabled: true }}
              wheel={{ disabled: true }}
              pinch={{ step: 5 }}
              panning={{ disabled: true }}
            >
              <TransformComponent wrapperClass="pdf-transform" contentClass="pdf-pages">
                <Document
                  file={{ url: pdfUrl }}
                  options={{
                    disableWorker: isIOS,
                    disableRange: true,
                    disableStream: true
                  }}
                  loading={null}
                  error={null}
                  onLoadSuccess={(pdf) => {
                    setNumPages(pdf.numPages);
                    setStatus("ready");
                  }}
                  onLoadError={() => setStatus("error")}
                >
                  {pages}
                </Document>
              </TransformComponent>
            </TransformWrapper>

            {status === "loading" && (
              <div className="loading">Ще трошечки почекай і все буде 🙏</div>
            )}
            {status === "error" && (
              <div className="loading">
                Не вдалося завантажити PDF. Перевірте посилання або спробуйте ще раз.
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
