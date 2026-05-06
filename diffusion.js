(function () {
  'use strict';

  function easeOutCubic(t) { return 1 - Math.pow(1 - t, 3); }

  /* ── ParticleText ── */
  function ParticleText(element, opts) {
    this.element = element;
    this.duration = opts.duration || 2200;
    this.spread = opts.spread || 60;
    this.particles = [];
    this.canvas = null;
    this.ctx = null;
    this.startTime = null;
    this.rect = null;
    this._boundAnimate = this.animate.bind(this);
  }

  ParticleText.prototype.start = function () {
    // First, make element visible briefly to measure and capture
    this.element.style.visibility = 'visible';
    this.element.style.opacity = '1';

    this.rect = this.element.getBoundingClientRect();
    this.createCanvas();
    this.captureElement();

    if (this.particles.length === 0) {
      // Fallback
      return;
    }

    this.scatterParticles();

    // Now hide the element
    this.element.style.visibility = 'hidden';

    requestAnimationFrame(this._boundAnimate);
  };

  ParticleText.prototype.createCanvas = function () {
    var rect = this.rect;
    var pad = this.spread * 2;
    var dpr = window.devicePixelRatio || 1;
    this.dpr = dpr;
    this.padCSS = pad;

    var cssW = rect.width + pad * 2;
    var cssH = rect.height + pad * 2;

    this.canvas = document.createElement('canvas');
    this.canvas.width = Math.ceil(cssW * dpr);
    this.canvas.height = Math.ceil(cssH * dpr);
    this.canvas.style.cssText =
      'position:fixed;pointer-events:none;z-index:100;' +
      'top:' + (rect.top - pad) + 'px;' +
      'left:' + (rect.left - pad) + 'px;' +
      'width:' + cssW + 'px;' +
      'height:' + cssH + 'px;';

    this.ctx = this.canvas.getContext('2d');
    document.body.appendChild(this.canvas);
  };

  ParticleText.prototype.captureElement = function () {
    // Create an offscreen canvas at the element's exact size to render its text
    var rect = this.rect;
    var dpr = this.dpr;
    var pad = this.padCSS;
    var styles = window.getComputedStyle(this.element);

    // We need to replicate the element's text rendering
    var offCanvas = document.createElement('canvas');
    var offW = Math.ceil(rect.width * dpr);
    var offH = Math.ceil(rect.height * dpr);
    offCanvas.width = offW;
    offCanvas.height = offH;
    var offCtx = offCanvas.getContext('2d');
    offCtx.scale(dpr, dpr);

    // Get all text nodes and their positions relative to the element
    var elRect = rect;
    var textNodes = [];
    this.getTextNodes(this.element, textNodes);

    // For each text node, get its position via Range API
    var fontSize = parseFloat(styles.fontSize);
    var fontWeight = styles.fontWeight;
    var fontFamily = styles.fontFamily;

    // Determine text color
    var r = 255, g = 255, b = 255, a = 1;
    var colorMatch = styles.color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/);
    if (colorMatch) {
      r = parseInt(colorMatch[1]);
      g = parseInt(colorMatch[2]);
      b = parseInt(colorMatch[3]);
      a = colorMatch[4] !== undefined ? parseFloat(colorMatch[4]) : 1;
    }

    // Use Range API to get exact position of each character
    offCtx.font = fontWeight + ' ' + fontSize + 'px ' + fontFamily;
    offCtx.fillStyle = 'rgba(' + r + ',' + g + ',' + b + ',' + a + ')';
    offCtx.textBaseline = 'top';

    for (var t = 0; t < textNodes.length; t++) {
      var node = textNodes[t];
      var text = node.textContent;
      var range = document.createRange();

      // Render character by character using Range for positioning
      for (var c = 0; c < text.length; c++) {
        range.setStart(node, c);
        range.setEnd(node, c + 1);
        var charRect = range.getBoundingClientRect();
        var ch = text[c];
        if (ch.trim() === '') continue;

        // Position relative to the element
        var cx = charRect.left - elRect.left;
        var cy = charRect.top - elRect.top;
        offCtx.fillText(ch, cx, cy);
      }
    }

    // Now sample from the offscreen canvas
    offCtx.setTransform(1, 0, 0, 1, 0, 0);
    var imageData = offCtx.getImageData(0, 0, offW, offH);
    var data = imageData.data;
    var step = Math.max(1, Math.round(dpr));

    for (var py = 0; py < offH; py += step) {
      for (var px = 0; px < offW; px += step) {
        var idx = (py * offW + px) * 4;
        var alpha = data[idx + 3];
        if (alpha > 10) {
          // Convert to CSS coordinates, offset by padding
          var cssX = px / dpr + pad;
          var cssY = py / dpr + pad;
          this.particles.push({
            x: cssX, y: cssY,
            targetX: cssX, targetY: cssY,
            startX: 0, startY: 0,
            r: data[idx], g: data[idx + 1], b: data[idx + 2],
            origAlpha: alpha / 255,
            currentAlpha: 0,
            delay: 0
          });
        }
      }
    }
  };

  ParticleText.prototype.getTextNodes = function (node, result) {
    if (node.nodeType === Node.TEXT_NODE) {
      if (node.textContent.trim().length > 0) {
        result.push(node);
      }
    } else {
      for (var i = 0; i < node.childNodes.length; i++) {
        this.getTextNodes(node.childNodes[i], result);
      }
    }
  };

  ParticleText.prototype.scatterParticles = function () {
    var spread = this.spread;
    var totalW = this.rect.width + this.padCSS * 2;

    this.particles.forEach(function (p) {
      var angle = Math.random() * Math.PI * 2;
      var dist = (Math.random() * 0.7 + 0.3) * spread;
      p.startX = p.targetX + Math.cos(angle) * dist;
      p.startY = p.targetY + Math.sin(angle) * dist;
      p.x = p.startX;
      p.y = p.startY;
      p.currentAlpha = 0;
      p.delay = (p.targetX / totalW) * 0.35 + Math.random() * 0.08;
    });
  };

  ParticleText.prototype.animate = function (timestamp) {
    if (!this.startTime) this.startTime = timestamp;
    var elapsed = timestamp - this.startTime;
    var progress = Math.min(elapsed / this.duration, 1);

    var ctx = this.ctx;
    var dpr = this.dpr;
    var cw = this.canvas.width;
    var ch = this.canvas.height;

    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, cw, ch);
    ctx.scale(dpr, dpr);

    var particles = this.particles;
    var dotSize = 1 / dpr + 0.3;

    for (var i = 0; i < particles.length; i++) {
      var p = particles[i];
      var pProgress = Math.max(0, Math.min(1, (progress - p.delay) / (1 - p.delay)));
      var eased = easeOutCubic(pProgress);

      p.x = p.startX + (p.targetX - p.startX) * eased;
      p.y = p.startY + (p.targetY - p.startY) * eased;
      p.currentAlpha = p.origAlpha * eased;

      if (p.currentAlpha > 0.005) {
        ctx.fillStyle = 'rgba(' + p.r + ',' + p.g + ',' + p.b + ',' + p.currentAlpha + ')';
        ctx.fillRect(p.x, p.y, dotSize, dotSize);
      }
    }

    if (progress < 1) {
      requestAnimationFrame(this._boundAnimate);
    } else {
      // Done — show original, remove canvas
      this.element.style.visibility = 'visible';
      var canvas = this.canvas;
      canvas.style.transition = 'opacity 0.3s ease';
      canvas.style.opacity = '0';
      setTimeout(function () { canvas.remove(); }, 400);
    }
  };

  /* ── Init ── */
  function init() {
    var badge = document.querySelector('.hero-badge');
    var heading = document.querySelector('.hero-heading');
    var subtitle = document.querySelector('.hero-subtitle');
    var ctas = document.querySelector('.hero-ctas');
    var navbar = document.querySelector('.navbar');

    [navbar, badge, heading, subtitle, ctas].forEach(function (el) {
      if (el) el.style.opacity = '0';
    });

    if (navbar) {
      setTimeout(function () {
        navbar.style.transition = 'opacity 0.8s ease';
        navbar.style.opacity = '1';
      }, 200);
    }

    if (badge) {
      setTimeout(function () {
        badge.style.transition = 'opacity 1s ease';
        badge.style.opacity = '1';
      }, 500);
    }

    if (heading) {
      setTimeout(function () {
        new ParticleText(heading, { duration: 2400, spread: 70 }).start();
      }, 800);
    }

    if (subtitle) {
      setTimeout(function () {
        new ParticleText(subtitle, { duration: 2800, spread: 40 }).start();
      }, 1400);
    }

    if (ctas) {
      setTimeout(function () {
        ctas.style.transition = 'opacity 1s ease';
        ctas.style.opacity = '1';
      }, 2200);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      document.fonts.ready.then(function () { setTimeout(init, 150); });
    });
  } else {
    document.fonts.ready.then(function () { setTimeout(init, 150); });
  }
})();
