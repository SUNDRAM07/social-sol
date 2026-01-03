import { useState } from "react";
import Card from "../components/ui/Card.jsx";
import Button from "../components/ui/Button.jsx";

function PricingTier({ name, price, features, cta }) {
  return (
    <Card className="text-center" variant="elevated">
      <div className="text-xl font-bold mb-2">{name}</div>
      <div className="text-3xl font-extrabold gradient-primary-text mb-4">{price}</div>
      <ul className="text-sm text-[var(--muted)] space-y-2 mb-4">
        {features.map((f, i) => (
          <li key={i}>{f}</li>
        ))}
      </ul>
      <Button variant="primary">{cta}</Button>
    </Card>
  );
}

function Pricing() {
  const [yearly, setYearly] = useState(false);
  const monthly = [
    { name: "Starter", price: "$9/mo", features: ["1 user", "Basic analytics"], cta: "Get started" },
    { name: "Pro", price: "$29/mo", features: ["5 users", "Advanced analytics"], cta: "Start trial" },
    { name: "Enterprise", price: "Contact us", features: ["Custom users", "SLA & onboarding"], cta: "Contact sales" },
  ];

  const yearlyPrices = [
    { ...monthly[0], price: "$90/yr" },
    { ...monthly[1], price: "$290/yr" },
    { ...monthly[2], price: "Contact us" },
  ];

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold gradient-primary-text">Pricing</h1>
          <p className="text-[var(--muted)]">Choose the plan that fits your team.</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-[var(--muted)]">Monthly</span>
          <label className="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" className="sr-only peer" checked={yearly} onChange={() => setYearly(!yearly)} />
            <div className="w-11 h-6 bg-[var(--border)] peer-checked:bg-[var(--primary)] rounded-full"></div>
          </label>
          <span className="text-sm text-[var(--muted)]">Yearly</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {(yearly ? yearlyPrices : monthly).map((p) => (
          <PricingTier key={p.name} {...p} />
        ))}
      </div>
    </div>
  );
}

export default Pricing;


