# Campus Customs: Storefront Design (Problem 10)

**Concept: "the varsity shop."** The site should feel like walking into a campus store on game day: chenille letter patches, felt pennants, Polaroids taped to the wall, paper hang tags on the rack, and a bulldog behind the counter. Everything stays in the black-and-pink palette, and every effect is there to keep shoppers browsing and help them buy.

## What changed and why

| Area | What I changed | Why it helps people stay and buy |
|---|---|---|
| **Fonts and hierarchy** | **Graduate** (collegiate block letters) for headings, prices, and the logo; **Caveat** handwriting for friendly asides ("everywhere you go.", "game day"); **Inter** for body text. Eyebrow labels with a pink rule, and a hand-drawn pink swash under section titles. | Instantly reads as *college apparel*, not a generic template. Three clear levels (varsity headline → script accent → readable body) tell the eye where to look first. |
| **Brand marks** | Chenille-patch "CC" logo (stitched dashed edge, tilts on hover); the subtitle "Yale apparel · New Haven"; a felt-grain texture over the whole site; a pennant-zigzag strip on the footer. | A memorable, tactile identity builds trust and makes the shop feel like a real store with a place on Broadway. |
| **Stadium ticker** | A pink scrolling marquee under the nav: "Boola Boola ✦ Officially licensed ✦ Visit us at 57 Broadway ✦ Ask the Bulldog Assistant about sizes & stock ✦ Beat Harvard". It pauses on hover. | Game-day energy, plus it quietly advertises the two things that build confidence: official licensing and the stock-checking assistant. |
| **Hero** | A giant varsity headline; three **real products as taped Polaroids** floating around the mascot (each links to its product page); a fluttering "BOOLA BOOLA" pennant; a pulsing pink spotlight; **live stats from the catalogue API** (102 styles · 467 sizes on the shelf · XS–XXL). | Shows actual merchandise in the first second, with one click straight to a product. The live stats signal "big selection, really in stock". |
| **Mascot** | The HTML/CSS bulldog now wears a pink-striped varsity sweater with a "CC" collar tag, **blinks**, and **wiggles its ears** on hover. | A character people want to poke keeps them on the page and gives the brand a face. The same bulldog runs the chat (below). |
| **Category pennants** | "Pick your pennant": swallow-tail felt pennants with stitched borders, alternating pink and black, each with a handwritten note ("warmest seats in the house") and a **live style count**. They link to the filtered Products page. | Turns category navigation into a fun, on-theme choice; the counts promise depth before the click. |
| **Product cards** | Garments on a soft spotlight background; a **paper hang tag** with the price, hanging on a pink string (it swings on hover); category label; **image zoom** and "View details →" on hover; an honest **"Only N sizes left" ribbon** (shown on about 1 in 5 products, the ones with ≤ 3 sizes in stock); staggered pop-in when the grid loads. | The hang tag makes price obvious and on-brand. Real scarcity cues (from inventory, never invented) encourage decisions. Hover feedback rewards exploring. |
| **Product page** | **Hover-to-zoom photo** that follows the cursor (like holding the shirt up close); stitched photo frame; price on a tilted hang tag; **size buttons styled as varsity number patches** (the selected size turns pink with stitching). | Shoppers can inspect print and fabric detail, which is the #1 thing a photo has to do online. Size selection feels tactile and clear. |
| **Chat feel** | The chat button **is the bulldog** (gently bobbing); a one-time **"Need a size or a gift idea? Ask me!"** speech bubble after 4 seconds; the header shows the bulldog avatar with a **green "online" pulse**; assistant messages have a mini bulldog avatar; typing shows **bouncing paw prints 🐾 "fetching…"**; messages and the panel pop in with a springy animation. | Makes the assistant feel like a friendly store employee, not a form. The nudge gets shy shoppers to ask, and the assistant is how they check sizes, find alternatives, and get to checkout-ready decisions. |
| **Motion system** | One springy easing curve for everything; scroll-reveal for sections and pennants; staggered card entrances. **All motion turns off for `prefers-reduced-motion`.** | Motion guides attention without getting in the way, and stays accessible. |

## A bug the design pass caught

While testing the chat on product pages, quickly asking "Is this in stock in M?" on a new product sometimes got an answer about the **previous** product, because an identical earlier question in the history outweighed the page note. Fixed in two places:
- The chat sends the product from the URL immediately.
- The backend now attaches "[Shopper is viewing right now: …]" to the shopper's current message.

Re-tested on 3 product pages in a row with the same history: all answers were correct and matched `inventory`.

## Files

- `frontend/src/storefront.css`: the new design layer (all styles above)
- `frontend/index.html`: Graduate, Caveat, and Inter fonts
- New components: `Marquee.tsx`, `Pennant.tsx`, `Reveal.tsx`, `MiniBulldog.tsx`
- Restyled: `pages/Home.tsx`, `components/ProductCard.tsx`, `components/Bulldog.tsx`, `components/NavBar.tsx`, `components/ChatWidget.tsx`, `pages/ProductDetail.tsx`
- Backend fix: `backend/agent.py → with_page_note()`
