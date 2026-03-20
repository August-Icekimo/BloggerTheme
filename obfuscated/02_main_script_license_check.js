/**
 * Obfuscated Block #2 — Main Theme Script (License Check + All Features)
 * ======================================================================
 * 
 * Source: Igniplex v3.1.xml, line 5732
 * Location: <b:includable id='script'>, inside <script>//[CDATA[ ... ]]</script>
 * Packer: Dean Edwards Packer (eval(function(p,a,c,k,e,d){...}))
 * Token Count: 2353 substitution tokens
 * 
 * This block is MASSIVE and contains the entire theme's runtime JavaScript,
 * including: infinite scroll, related posts, TOC generation, bookmarks,
 * carousel, speech synthesis, dark mode toggle, letter style, ads detection,
 * AND the license/authorization check that causes the redirect.
 * 
 * Full deobfuscation of 2300+ tokens is impractical to present as clean code.
 * Below we document the KEY DECODED STRINGS and the LICENSE CHECK LOGIC
 * reconstructed from the obfuscated source.
 * 
 * Risk Level: HIGH (contains remote fetch + conditional redirect)
 */


// =============================================================================
// SECTION 1: DECODED HEX STRINGS (used for domain whitelist & API communication)
// =============================================================================

// These strings are hex-encoded in the source to evade simple text search.
// Format: each character is encoded as a 4-digit hex UTF-16 code unit.

const DECODED_STRINGS = {
  // --- License API ---
  API_URL_PREFIX:    "https://source.igniel.com/api?key=",  // l7
  API_PARAM_1:       "&id=ign&v=3.1",                       // kR
  API_PARAM_2:       "&url=",                                // kQ

  // --- Domain Whitelist (requests from these domains skip license check) ---
  WHITELIST: [
    "Speed",                                        // kp (Lighthouse/PageSpeed user agent)
    "Lighthouse",                                   // kj
    "google.com",                                   // ks
    "adsense.com",                                  // ku
    "googleapis.com",                               // kr
    "google-analytics.com",                         // kh
    "googleusercontent.com",                        // k2
    "blogger.com",                                  // kd
    "gstatic.com",                                  // kc
    "histatsi.com",                                 // k9  (typo in original, likely histats.com)
    "cloudflare.com",                               // k8
    "pingdom.com",                                  // k7
    "googletagaanager.com",                         // k4  (typo in original, likely googletagmanager.com)
    "autoads-preview.googleusercontent.com",        // kU
    "translate.goog",                               // kX
    "withgoogle.com",                               // kY
    "gtmetrix.com",                                 // kZ
    "web.dev",                                      // l0
    "bing.com",                                     // l2
    "neilpatel.com",                                // l6
  ],

  // --- Cookie Management ---
  COOKIE_CLEAR:      "=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT;",  // kT
  COOKIE_PATH:       "; path=/",                                             // k3
  COOKIE_EXPIRES:    "expires=",

  // --- Error Messages ---
  LICENSE_ERROR:     "License error. Cannot get data",   // kg
  IGNIPLEX_LABEL:   "(IGNIPLEX)",
  
  // --- Additional hostname checks (used in userAgent/referrer matching) ---
  HOSTNAME_CHECK_1: "neilpatel.com",     // pj
  HOSTNAME_CHECK_2: "google.co.id",      // ph
  HOSTNAME_CHECK_3: "doubleclick.net",   // pV
};


// =============================================================================
// SECTION 2: RECONSTRUCTED LICENSE CHECK LOGIC (pseudo-code)
// =============================================================================

/**
 * The license check runs inside a Promise with a setInterval.
 * Here is the reconstructed flow:
 * 
 * 1. Compute a cookie name by hex-encoding the blogId (data-blog attribute).
 * 
 * 2. Check if a cookie with that name already exists:
 *    - If YES and value is not empty → license previously validated, SKIP check.
 *    - If NO or empty → proceed to remote validation.
 * 
 * 3. If no valid cookie, AND the current page is not in preview mode:
 *    a. Build the API URL:
 *       ```
 *       https://source.igniel.com/api?key=<blogId>&id=ign&v=3.1&url=<currentHostname>
 *       ```
 *    b. Fetch the API response as JSON.
 * 
 * 4. On successful response:
 *    a. Check if `response.ref.origin === currentHostname`:
 *       - If YES (domain matches): Set a cookie with an expiry date to cache
 *         the license validation. The page loads normally.
 *       - If NO (domain mismatch): Check if the hostname is in the WHITELIST.
 *         - If in whitelist → allow (these are crawlers/tools).
 *         - If NOT in whitelist → **REDIRECT** after a timeout:
 *           ```js
 *           setTimeout(() => {
 *             location.href = response.ref.url + '?ref=' + currentHostname
 *           }, delay);
 *           ```
 *           This redirects to something like:
 *           https://igniplex.blogspot.com/p/contact.html?ref=blog.icekimo.idv.tw
 * 
 * 5. On fetch error:
 *    - Log: "License error. Cannot get data" + error details to console.
 *    - Also redirect (same mechanism as step 4).
 * 
 * 6. If cookie exists and is valid:
 *    - Skip the entire remote check.
 *    - Proceed to enable interactive features (dark mode toggle, bookmarks,
 *      TOC, related posts, carousels, text-to-speech, etc.)
 */


// =============================================================================
// SECTION 3: IMPORTANT VARIABLE MAPPING (partial)
// =============================================================================

/**
 * These are some key variable-to-meaning mappings identified in the script:
 * 
 * Variable    | Meaning
 * ------------|---------------------------------------------------
 * 4C          | hex-encoded cookie name (derived from blogId)
 * kb          | decoded error message ("License error...")
 * cU()        | function: checks if a cookie exists by name
 * cT()        | function: reads a cookie value by name
 * kA()        | function: hex-encodes a string (blogId → cookie key)
 * 19()        | function: hex-decodes a string (4-digit hex → chars)
 * 6Q          | current hostname (document.location.hostname)
 * l1          | blogId (from data-blog attribute)
 * kG          | array of 20 whitelisted domains (decoded from hex)
 * kP          | redirect delay (in milliseconds)
 * g1()        | fetch() wrapper
 * 6E          | API response JSON object
 * 6E.ref      | license reference object (contains .url, .origin)
 * 6E.ref.url  | redirect target URL (e.g. igniplex.blogspot.com/p/contact.html)
 * 6E.bk       | (alias for ref in some paths)
 */
