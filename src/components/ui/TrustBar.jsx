const logos = [
  "/public/placeholder_f324cd30_1755853779.png",
  "/public/placeholder_5eb63bbb_1755865616.png",
  "/public/placeholder_f498829f_1755864397.png",
  "/public/placeholder_5f585d3b_1755856052.png",
  "/public/placeholder_08256e59_1755866483.png",
];

function TrustBar() {
  return (
    <div className="mt-8 bg-transparent overflow-x-auto py-4">
      <div className="max-w-7xl mx-auto px-6 flex items-center gap-8">
        {logos.map((l, idx) => (
          <img key={idx} src={l} alt={`logo-${idx}`} className="h-8 opacity-70 grayscale" />
        ))}
      </div>
    </div>
  );
}

export default TrustBar;


