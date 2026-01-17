import React, { useEffect, useMemo, useRef, useState } from "react";

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

export default function App() {
  const containerRef = useRef(null);
  const pageWrappersRef = useRef([]);
  const observerRef = useRef(null);
  const renderIdRef = useRef(0);
  const isRenderingRef = useRef(false);
  const resizeTimerRef = useRef(null);
  const linkServiceRef = useRef(null);
  const currentPageRef = useRef(1);
  const scaleRef = useRef(1);
  const pinchRef = useRef({
    active: false,
    startDistance: 0,
    startScale: 1,
    raf: 0,
    nextScale: 1
  });

  const [{ pdfUrl, filename }] = useState(getViewerConfig);
  const [pdfDoc, setPdfDoc] = useState(null);
  const [status, setStatus] = useState("loading");
  const [scale, setScale] = useState(1);
  const [pageCount, setPageCount] = useState(1);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageInput, setPageInput] = useState("1");
  const [isEditing, setIsEditing] = useState(false);

  const pdfjs = window.pdfjsLib;
  const pdfjsViewer = window.pdfjsViewer;
  const isIOS = useMemo(
    () => /iP(ad|hone|od)/.test(navigator.userAgent || ""),
    []
  );

  useEffect(() => {
    if (!pdfjs) {
      setStatus("error");
      return;
    }

    pdfjs.GlobalWorkerOptions.workerSrc =
      "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";

    if (pdfjsViewer && pdfjsViewer.SimpleLinkService) {
      linkServiceRef.current = new pdfjsViewer.SimpleLinkService();
      if (pdfjsViewer.LinkTarget) {
        linkServiceRef.current.externalLinkTarget = pdfjsViewer.LinkTarget.BLANK;
      }
    }

    setStatus("loading");
    pdfjs
      .getDocument({ url: pdfUrl, disableWorker: isIOS })
      .promise.then((pdf) => {
        if (linkServiceRef.current && linkServiceRef.current.setDocument) {
          linkServiceRef.current.setDocument(pdf);
        }
        setPdfDoc(pdf);
        setPageCount(pdf.numPages);
        setStatus("ready");
      })
      .catch(() => {
        setStatus("error");
      });
  }, [pdfjs, pdfjsViewer, pdfUrl]);

  useEffect(() => {
    if (!pdfDoc || !containerRef.current) return;
    let cancelled = false;

    pdfDoc.getPage(1).then((page) => {
      if (cancelled) return;
      const fit = getFitScale(page);
      setScale(fit);
    });

    return () => {
      cancelled = true;
    };
  }, [pdfDoc]);

  useEffect(() => {
    if (!pdfDoc || !containerRef.current || !pdfjs) return;

    let cancelled = false;
    const renderId = ++renderIdRef.current;

    const renderAllPages = async () => {
      if (isRenderingRef.current) return;
      isRenderingRef.current = true;
      clearPages();

      for (let pageNum = 1; pageNum <= pdfDoc.numPages; pageNum += 1) {
        if (cancelled || renderId !== renderIdRef.current) break;
        await renderPage(pageNum);
      }

      if (!cancelled && renderId === renderIdRef.current) {
        attachPageObservers();
        scrollToPage(currentPageRef.current, "auto");
      }

      isRenderingRef.current = false;
    };

    renderAllPages();

    return () => {
      cancelled = true;
      isRenderingRef.current = false;
    };
  }, [pdfDoc, pdfjs, scale]);

  useEffect(() => {
    scaleRef.current = scale;
    if (!pdfDoc) return;
    if (!isEditing) {
      setPageInput(String(currentPage));
    }
  }, [currentPage, isEditing]);

  useEffect(() => {
    if (!pdfDoc) return;

    const handleResize = () => {
      clearTimeout(resizeTimerRef.current);
      resizeTimerRef.current = setTimeout(() => {
        pdfDoc.getPage(1).then((page) => {
          setScale(getFitScale(page));
        });
      }, 160);
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [pdfDoc]);

  const updateZoom = (nextScale) => {
    setScale(clamp(nextScale, 0.6, 2.8));
  };

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const getDistance = (touches) => {
      const [t1, t2] = touches;
      const dx = t1.clientX - t2.clientX;
      const dy = t1.clientY - t2.clientY;
      return Math.hypot(dx, dy);
    };

    const scheduleScale = (nextScale) => {
      pinchRef.current.nextScale = nextScale;
      if (pinchRef.current.raf) return;
      pinchRef.current.raf = window.requestAnimationFrame(() => {
        pinchRef.current.raf = 0;
        updateZoom(pinchRef.current.nextScale);
      });
    };

    const onTouchStart = (event) => {
      if (event.touches.length !== 2) return;
      pinchRef.current.active = true;
      pinchRef.current.startDistance = getDistance(event.touches);
      pinchRef.current.startScale = scaleRef.current;
    };

    const onTouchMove = (event) => {
      if (!pinchRef.current.active || event.touches.length !== 2) return;
      event.preventDefault();
      const currentDistance = getDistance(event.touches);
      const ratio = currentDistance / pinchRef.current.startDistance;
      const nextScale = pinchRef.current.startScale * ratio;
      scheduleScale(clamp(nextScale, 0.6, 2.8));
    };

    const onTouchEnd = () => {
      pinchRef.current.active = false;
    };

    const onWheel = (event) => {
      if (!event.ctrlKey) return;
      event.preventDefault();
      const factor = Math.exp(-event.deltaY / 300);
      updateZoom(clamp(scaleRef.current * factor, 0.6, 2.8));
    };

    container.addEventListener("touchstart", onTouchStart, { passive: false });
    container.addEventListener("touchmove", onTouchMove, { passive: false });
    container.addEventListener("touchend", onTouchEnd, { passive: true });
    container.addEventListener("touchcancel", onTouchEnd, { passive: true });
    container.addEventListener("wheel", onWheel, { passive: false });

    return () => {
      container.removeEventListener("touchstart", onTouchStart);
      container.removeEventListener("touchmove", onTouchMove);
      container.removeEventListener("touchend", onTouchEnd);
      container.removeEventListener("touchcancel", onTouchEnd);
      container.removeEventListener("wheel", onWheel);
    };
  }, []);

  const onPageInputChange = (event) => {
    setPageInput(event.target.value);
  };

  const onPageInputCommit = () => {
    if (!pdfDoc) return;
    const value = parseInt(pageInput, 10);
    if (Number.isNaN(value)) {
      setPageInput(String(currentPage));
      return;
    }
    const safeValue = clamp(value, 1, pdfDoc.numPages);
    setPageInput(String(safeValue));
    setCurrentPage(safeValue);
    currentPageRef.current = safeValue;
    scrollToPage(safeValue, "smooth");
  };

  const getFitScale = (page) => {
    if (!containerRef.current) return 1;
    const viewport = page.getViewport({ scale: 1 });
    const padding = 60;
    const maxWidth = containerRef.current.clientWidth - padding;
    if (maxWidth <= 0) return 1;
    return clamp(maxWidth / viewport.width, 0.6, 2.2);
  };

  const clearPages = () => {
    if (!containerRef.current) return;
    containerRef.current.innerHTML = "";
    pageWrappersRef.current = [];
    if (observerRef.current) {
      observerRef.current.disconnect();
      observerRef.current = null;
    }
  };

  const attachPageObservers = () => {
    if (!("IntersectionObserver" in window) || !containerRef.current) return;

    observerRef.current = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const pageNum = parseInt(entry.target.dataset.pageNum, 10);
            if (!Number.isNaN(pageNum)) {
              currentPageRef.current = pageNum;
              setCurrentPage(pageNum);
            }
          }
        });
      },
      { root: containerRef.current, threshold: 0.5 }
    );

    pageWrappersRef.current.forEach((wrapper) => {
      observerRef.current.observe(wrapper);
    });
  };

  const renderPage = async (pageNum) => {
    const page = await pdfDoc.getPage(pageNum);
    const viewport = page.getViewport({ scale });

    const wrapper = document.createElement("div");
    wrapper.className = "page-shell";
    wrapper.dataset.pageNum = String(pageNum);
    wrapper.style.setProperty("--scale-factor", viewport.scale);

    const canvas = document.createElement("canvas");
    canvas.height = viewport.height;
    canvas.width = viewport.width;
    wrapper.appendChild(canvas);

    const textLayerDiv = document.createElement("div");
    textLayerDiv.className = "textLayer";
    textLayerDiv.style.setProperty("--scale-factor", viewport.scale);
    wrapper.appendChild(textLayerDiv);

    const annotationLayerDiv = document.createElement("div");
    annotationLayerDiv.className = "annotationLayer";
    annotationLayerDiv.style.setProperty("--scale-factor", viewport.scale);
    wrapper.appendChild(annotationLayerDiv);

    containerRef.current.appendChild(wrapper);
    pageWrappersRef.current.push(wrapper);

    await page.render({ canvasContext: canvas.getContext("2d"), viewport }).promise;

    const textContent = await page.getTextContent();
    const textLayerTask = pdfjs.renderTextLayer({
      textContentSource: textContent,
      container: textLayerDiv,
      viewport,
      textDivs: [],
      enhanceTextSelection: false
    });

    if (textLayerTask && textLayerTask.promise) {
      await textLayerTask.promise;
    }

    const annotations = await page.getAnnotations({ intent: "display" });
    await renderLinkAnnotations(annotations, viewport, annotationLayerDiv);
  };

  const renderLinkAnnotations = async (annotations, viewport, layer) => {
    layer.innerHTML = "";
    if (!annotations || !annotations.length) return;

    for (const annotation of annotations) {
      if (annotation.subtype !== "Link") continue;

      const [x1, y1, x2, y2] = viewport.convertToViewportRectangle(
        annotation.rect
      );
      const left = Math.min(x1, x2);
      const top = Math.min(y1, y2);
      const width = Math.abs(x1 - x2);
      const height = Math.abs(y1 - y2);

      const link = document.createElement("a");
      link.className = "link-annotation";
      link.style.left = `${left}px`;
      link.style.top = `${top}px`;
      link.style.width = `${width}px`;
      link.style.height = `${height}px`;

      if (annotation.url) {
        link.href = annotation.url;
        link.target = "_blank";
        link.rel = "noopener";
      } else if (annotation.dest) {
        link.href = "#";
        link.addEventListener("click", async (event) => {
          event.preventDefault();
          const targetPage = await resolveDestination(annotation.dest);
          if (targetPage) {
            setCurrentPage(targetPage);
            currentPageRef.current = targetPage;
            scrollToPage(targetPage, "smooth");
          }
        });
      } else {
        continue;
      }

      layer.appendChild(link);
    }
  };

  const resolveDestination = async (dest) => {
    if (!pdfDoc) return null;
    let destArray = dest;
    if (!Array.isArray(destArray)) {
      destArray = await pdfDoc.getDestination(dest);
    }
    if (!destArray || !destArray.length) return null;
    const pageRef = destArray[0];
    try {
      if (typeof pageRef === "object") {
        const pageIndex = await pdfDoc.getPageIndex(pageRef);
        return pageIndex + 1;
      }
      if (typeof pageRef === "number") {
        return pageRef + 1;
      }
    } catch (_) {
      return null;
    }
    return null;
  };

  const scrollToPage = (pageNum, behavior) => {
    const target = pageWrappersRef.current[pageNum - 1];
    if (target) {
      target.scrollIntoView({ behavior, block: "start" });
    }
  };

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-inner">
          <div className="title-block">
            <div className="badge">PDF</div>
            <div className="title-text">
              <h1>Тренування</h1>
              <span>{filename}</span>
            </div>
          </div>
          <div className="controls">
            <div className="control-group">
              <input
                className="page-input"
                type="number"
                min="1"
                value={pageInput}
                onChange={onPageInputChange}
                onFocus={() => setIsEditing(true)}
                onBlur={() => {
                  setIsEditing(false);
                  onPageInputCommit();
                }}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.target.blur();
                  }
                }}
                disabled={status !== "ready"}
              />
              <div className="page-total">/ {pageCount}</div>
            </div>
          </div>
        </div>
      </header>

      <main className="viewer">
        <section className="viewer-shell">
          <div className="pdf-container" ref={containerRef}>
            {status === "loading" && <div className="loading">Завантажуємо PDF…</div>}
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
