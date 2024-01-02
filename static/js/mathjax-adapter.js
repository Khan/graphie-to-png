// Adapt MathJax to look like KaTeX, so Khan Exercises can use it.
// The MathJaxRenderer global comes from mathjax-renderer.min.js in the
// @khanacademy/mathjax-renderer NPM package.
const renderer = new window.MathJaxRenderer({
    fontURL: "https://cdn.kastatic.org/fonts/mathjax",
    shouldFixUnicodeLayout: true,
});

window.katex = {
    render(tex, container) {
        // We ignore the error returned from renderer.render(), since Khan
        // Exercises can't do anything to recover from it if we throw. If
        // there is an error, domElement will still be non-null; it will
        // contain the malformed TeX or an error message.
        const {domElement} = renderer.render(tex);
        container.innerHTML = "";
        container.appendChild(domElement);
        renderer.updateStyles();
    }
};
