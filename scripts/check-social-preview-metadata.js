#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");

const siteRoot = path.resolve(__dirname, "..");
const imageUrl = "https://www.qadam.trade/assets/ibm-quantum-computer.jpg";
const imagePath = path.join(siteRoot, "assets", "ibm-quantum-computer.jpg");
const pages = [
    ["index.html", "https://www.qadam.trade/"],
    ["dashboard/index.html", "https://www.qadam.trade/dashboard/"],
    ["whitepaper/index.html", "https://www.qadam.trade/whitepaper/"],
    ["guide/index.html", "https://www.qadam.trade/guide/"],
    ["login/index.html", "https://www.qadam.trade/login/"],
    ["sign-up/index.html", "https://www.qadam.trade/sign-up/"]
];

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

function occurrences(value, needle) {
    return value.split(needle).length - 1;
}

function jpegDimensions(buffer) {
    assert(buffer[0] === 0xff && buffer[1] === 0xd8, "social_preview_image_not_jpeg");
    let offset = 2;
    while (offset + 9 < buffer.length) {
        if (buffer[offset] !== 0xff) {
            offset += 1;
            continue;
        }
        const marker = buffer[offset + 1];
        offset += 2;
        if (marker === 0xd8 || marker === 0xd9) continue;
        const length = buffer.readUInt16BE(offset);
        if ([0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf].includes(marker)) {
            return {
                height: buffer.readUInt16BE(offset + 3),
                width: buffer.readUInt16BE(offset + 5)
            };
        }
        assert(length >= 2, "social_preview_image_invalid_segment");
        offset += length;
    }
    throw new Error("social_preview_image_dimensions_missing");
}

const image = fs.readFileSync(imagePath);
const dimensions = jpegDimensions(image);
assert(dimensions.width === 1280, `social_preview_image_width_${dimensions.width}`);
assert(dimensions.height === 720, `social_preview_image_height_${dimensions.height}`);
assert(image.byteLength > 100_000 && image.byteLength < 5_000_000, "social_preview_image_size_out_of_bounds");

for (const [relativePath, canonicalUrl] of pages) {
    const html = fs.readFileSync(path.join(siteRoot, relativePath), "utf8");
    const label = relativePath.replaceAll("/", "_");
    const required = [
        `<link rel="canonical" href="${canonicalUrl}">`,
        '<meta property="og:site_name" content="Qadam">',
        `<meta property="og:url" content="${canonicalUrl}">`,
        `<meta property="og:image" content="${imageUrl}">`,
        `<meta property="og:image:secure_url" content="${imageUrl}">`,
        '<meta property="og:image:type" content="image/jpeg">',
        '<meta property="og:image:width" content="1280">',
        '<meta property="og:image:height" content="720">',
        '<meta property="og:image:alt" content="IBM quantum computer used in Qadam\'s hybrid research system">',
        '<meta name="twitter:card" content="summary_large_image">',
        `<meta name="twitter:image" content="${imageUrl}">`,
        `<link rel="image_src" href="${imageUrl}">`
    ];
    for (const snippet of required) {
        assert(html.includes(snippet), `${label}_missing_${snippet}`);
    }
    assert(occurrences(html, 'property="og:image"') === 1, `${label}_og_image_count_invalid`);
    assert(/<meta property="og:title" content="[^"<>]+">/.test(html), `${label}_og_title_missing`);
    assert(/<meta property="og:description"[\s\S]*?content="[^"<>]+">/.test(html), `${label}_og_description_missing`);
    assert(/<meta name="twitter:title" content="[^"<>]+">/.test(html), `${label}_twitter_title_missing`);
    assert(/<meta name="twitter:description"[\s\S]*?content="[^"<>]+">/.test(html), `${label}_twitter_description_missing`);
}

console.log("qadam_social_preview_metadata=ok");
console.log(`qadam_social_preview_page_count=${pages.length}`);
console.log(`qadam_social_preview_image=${imageUrl}`);
console.log(`qadam_social_preview_dimensions=${dimensions.width}x${dimensions.height}`);
console.log(`qadam_social_preview_bytes=${image.byteLength}`);
