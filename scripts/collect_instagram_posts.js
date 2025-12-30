/**
 * Instagram Post Collector
 *
 * Collects all post shortcodes from an Instagram profile page by scrolling
 * through the feed. Instagram uses virtual scrolling which removes posts
 * from the DOM as you scroll, so this script captures them before they disappear.
 *
 * USAGE:
 * 1. Open the Instagram profile page in your browser
 * 2. Open browser DevTools (F12 or Cmd+Shift+I)
 * 3. Go to Console tab
 * 4. Paste this entire script and press Enter
 * 5. Wait for "Done!" message (may take several minutes for large profiles)
 * 6. The shortcodes JSON array is automatically copied to clipboard
 * 7. Paste into a file: shortcodes.json
 *
 * OUTPUT FORMAT:
 * JSON array of shortcode strings, e.g.:
 * ["C78ldQ7qNDj", "C6x4evEK50x", "DScvrTgiGAC", ...]
 *
 * THEN USE WITH CLI:
 * python -m src.cli parse-shortcodes shortcodes.json -o videos.json
 */

(function collectInstagramPosts() {
  const collected = new Set();
  let lastCount = 0;
  let stableRounds = 0;
  const MAX_STABLE_ROUNDS = 5;
  const SCROLL_INTERVAL_MS = 1500;

  console.log('Starting Instagram post collection...');
  console.log('Scroll will continue until no new posts are found for', MAX_STABLE_ROUNDS, 'rounds');

  const scroll = setInterval(() => {
    // Grab all current shortcodes from links
    document.querySelectorAll('a[href*="/p/"], a[href*="/reel/"]').forEach(a => {
      const match = a.href.match(/\/(p|reel)\/([A-Za-z0-9_-]+)/);
      if (match) collected.add(match[2]);
    });

    console.log(`Collected: ${collected.size} posts (stable rounds: ${stableRounds}/${MAX_STABLE_ROUNDS})`);

    // Check if we're still finding new posts
    if (collected.size === lastCount) {
      stableRounds++;
      if (stableRounds >= MAX_STABLE_ROUNDS) {
        clearInterval(scroll);
        const result = JSON.stringify([...collected], null, 2);
        console.log('='.repeat(50));
        console.log('Done! Collected', collected.size, 'posts');
        console.log('='.repeat(50));

        // Try to copy to clipboard
        try {
          copy(result);
          console.log('Result copied to clipboard!');
        } catch (e) {
          console.log('Could not copy to clipboard. Copy manually:');
        }

        console.log(result);
        return;
      }
    } else {
      stableRounds = 0;
      lastCount = collected.size;
    }

    window.scrollTo(0, document.body.scrollHeight);
  }, SCROLL_INTERVAL_MS);

  // Provide a way to stop manually
  window.stopCollection = () => {
    clearInterval(scroll);
    const result = JSON.stringify([...collected], null, 2);
    console.log('Manually stopped. Collected', collected.size, 'posts');
    try {
      copy(result);
      console.log('Result copied to clipboard!');
    } catch (e) {
      console.log(result);
    }
  };

  console.log('Tip: Run stopCollection() to stop early and get current results');
})();
