var casper = require('casper').create({
    viewportSize: {
        wdith: 1024,
        height: 768
    },
    pageSettings: {
        loadImages:  false,        // do not load images
        loadPlugins: false         // do not load NPAPI plugins (Flash, Silverlight, ...)
    },
    verbose: false,
    logLevel: 'debug'
});

var x = require('casper').selectXPath;
var wq_data = {};

casper.start('http://www.wowhead.com/world-quests/na', function() {
    this.waitUntilVisible(x('//div[@id="lv-lv-world-quests"]'), function() {
        wq_data['wq'] = this.evaluate(function() { 
            wq = [];
	    lvWorldQuests['data'].forEach(function(x) { delete x.__tr; wq.push(x); });
            return wq;
         });

        wq_data['items'] = this.evaluate(function() { return g_items; });
        wq_data['quests'] = this.evaluate(function() { return g_quests; });
        wq_data['zones'] = this.evaluate(function() { return g_zones; });
        wq_data['factions'] = this.evaluate(function() { return g_factions; });
    }); 
});

casper.run(function() {
    this.echo(JSON.stringify(wq_data)).exit();
});
