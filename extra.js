// Hide base attributes for procs

$('div[id^="biopipen.ns."]').each(function() {
    let node = $(this);
    let parts = node.attr('id').split('.');
    if (parts.length == 3) {
        return;
    }
    node.find(".mkapi-section.attributes").remove();
    node.find(".mkapi-section.classes").remove();
    node.find(".mkapi-section.methods").remove();
    node.find(".mkapi-members").remove();

    // format items
    node.find(".mkapi-section-body > p").each(function() {
        let p = $(this);
        let lines = p.html().split("\n");
        if (/^(Input|Output|Envs|Requires):$/.test(lines[0])) {
            let items = [];
            console.log(lines);
            for (let i = 0; i < lines.length; i++) {
                if (i === 0) { continue; }
                if (lines[0] === "Requires:" && /^\s+-? \w+:\s*(\| )?/.test(lines[i])) {
                    let key = lines[i].replace(/^\s+(-? \w+:\s*(?:\| )?).+/, "$1");
                    let val = lines[i].replace(/^\s+-? \w+:\s*(?:\| )?/, "");
                    // console.log(key, "-", val);
                    let kls = key[0] === "-" ? " mkapi-item-first" : "";
                    items.push(
                        '<code class="mkapi-item-name' + kls + '">'
                        + key.replace(/(^[\s-]+|[:\|\s]+$)/g, "")
                        + '</code>'
                        + '<span class="mkapi-item-dash"> — </span>'
                        + '<code>' + val + '</code>'
                        + '<br />'
                    );
                } else if (/^    [\w_. -]+: /.test(lines[i])) {
                    let br = (i === 1) ? "" : "<br />";
                    items.push(br + lines[i].replace(
                        /^    ([\w_.-]+): /,
                        '<code class="mkapi-item-name">$1</code>'
                        + '<span class="mkapi-item-dash"> — </span>'
                    ));
                } else if (/^\s*-.+/.test(lines[i])) {
                    items.push("<br />" + lines[i]);
                } else if (lines[0] === "Requires:") {
                    items.push('<code class="pipen-requires-check-code">' + lines[i] + "</code>");
                } else {
                    items.push(lines[i]);
                }
            }
            let require_kls = (lines[0] === "Requires:") ? " pipen-requires" : "";
            p.addClass("proc-attr").html(
                '<div class="mkapi-section' + require_kls + '">'
                + '<div class="mkapi-section-name">'
                + '<span class="mkapi-section-name-body">'
                + lines[0]
                + '</span>'
                + '</div>'
                + '<div class="mkapi-section-body">'
                + items.join("\n")
                + '</div>'
                + '</div>'
            );
        }
    });
});

// sub-list items

const linkify = function(inputText) {
    var replacedText, replacePattern1, replacePattern2, replacePattern3;

    //URLs starting with http://, https://, or ftp://
    replacePattern1 = /(?<!href=")(\b(https?|ftp):\/\/[-A-Z0-9+&@#\/%?=~_|!:,.;]*[-A-Z0-9+&@#\/%=~_|])/gim;
    replacedText = inputText.replace(replacePattern1, '<a href="$1" target="_blank">$1</a>');

    //URLs starting with "www." (without // before it, or it'd re-link the ones done above).
    // replacePattern2 = /(^|[^\/])(www\.[\S]+(\b|$))/gim;
    // replacedText = replacedText.replace(replacePattern2, '$1<a href="http://$2" target="_blank">$2</a>');

    //Change email addresses to mailto:: links.
    // replacePattern3 = /(([a-zA-Z0-9\-\_\.])+@[a-zA-Z\_]+?(\.[a-zA-Z]{2,6})+)/gim;
    // replacedText = replacedText.replace(replacePattern3, '<a href="mailto:$1">$1</a>');

    return replacedText;
}

const replacer = function(match, p1, p2, offset, string, groups) {
    p1 = p1.replace("<", "&lt;").replace(">", "&gt;");
    return p2
        ? `<code>${p1}</code><span class="mkapi-item-type sub">${p2}</span>:`
        : `<code>${p1}</code>:`;
};

$(
    "div.mkapi-section.envs span.mkapi-item-description li, " +
    "div.mkapi-section.input span.mkapi-item-description li, " +
    "div.mkapi-section.output span.mkapi-item-description li " +
    "div.mkapi-section.requires span.mkapi-item-description li"
).each(function() {
    let html = $(this).html();
    // sub list items
    html = linkify(html).replaceAll(
        /<br>&nbsp;\s+- (.+?)( \(.+?\))?:/g,
        (m, p1, p2) => `<br />- ${replacer(m, p1, p2)}`
    ).replace(
        /^- (.+?)( \(.+?\))?:/,
        replacer
    );
    $(this).html(html);
});

$("blockquote:has(>blockquote>blockquote)").each(function(){
    $(this).replaceWith(`<pre><code>${$(this).text().replace(/\n{2,}/g, "\n")}</code></pre>`);
});

// TOC
$('div.md-sidebar--secondary nav.md-nav--secondary nav.md-nav a.md-nav__link[href^="#biopipenns"]')
    .next()
    .remove();
