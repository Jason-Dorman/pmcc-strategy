// Vitest's setup: jsdom has no canvas, and ECharts asks for a 2D context to measure text even
// when it draws SVG. jsdom answers null after logging "not implemented" for every chart; this
// answers null without the log, which is all a chart in a test needs.
HTMLCanvasElement.prototype.getContext = () => null;

// jsdom lays nothing out, so it has no scrollIntoView; a table scrolling to the row a reader
// arrived for (the Trade rules page) needs one that does nothing.
Element.prototype.scrollIntoView = () => undefined;
