var page = require('webpage').create();
var system = require('system');

page.onCallback = function(data) {
    console.log(page.evaluate(function() {
        return JSON.stringify({
            svg: window.getSVG(),
            other_data: JSON.stringify(window.getData())
        });
    }));

    phantom.exit();
};

var postData = 'js=' + encodeURIComponent(system.args[1] || "");

page.open('http://localhost:8765/svgize', 'POST', postData, function() {});
