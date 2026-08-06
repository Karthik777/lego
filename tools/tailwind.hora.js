/* Tailwind config for the hora block — see tools/tailwind_build.py.
   Both sources matter: the shell's classes are in page.html, and every class the hora grid
   and the status lines use exists only as a literal inside hora.js's template strings.
   Paths are relative to the repo root, which is where the build script runs. */
module.exports = {
    content: ['./lego/hora/page.html', './lego/hora/hora.js'],
    theme: { extend: {} },
    plugins: [],
};
