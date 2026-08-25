/* ==========================================================================
   PORTFOLIO SITE  -  main.js
   ライブラリ不要。全ページ共通で読み込みます。
     1. モバイルメニュー開閉
     2. ヘッダーのスクロール状態
     3. スクロールに応じたフェードイン（.reveal）
     4. カテゴリー絞り込み（WORKS）
     5. ページトップへ戻るボタン
     6. コピーライトの年号自動更新
     7. お問い合わせフォームの送信ダミー処理
     8. 見出しを1文字ずつに分割（data-anim="chars"）
     9. リンク・ボタンの文字をホバーで入れ替える準備
    10. 画像を押して詳細をポップアップ表示
    11. スライドカード（前後ボタン・カウンター・ドラッグ）
   ========================================================================== */
(function () {
  "use strict";

  /* ------------------------------------------ 1. モバイルメニュー開閉 */
  var burger = document.querySelector(".burger");
  var nav = document.querySelector(".nav");

  if (burger && nav) {
    var toggleNav = function (open) {
      burger.classList.toggle("is-open", open);
      nav.classList.toggle("is-open", open);
      burger.setAttribute("aria-expanded", String(open));
      document.body.style.overflow = open ? "hidden" : "";
    };

    burger.addEventListener("click", function () {
      toggleNav(!nav.classList.contains("is-open"));
    });

    // メニュー内のリンクを押したら閉じる
    nav.addEventListener("click", function (e) {
      if (e.target.closest("a")) toggleNav(false);
    });

    // Esc キーで閉じる
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && nav.classList.contains("is-open")) {
        toggleNav(false);
        burger.focus();
      }
    });

    // PC幅に戻ったら状態をリセット
    window.addEventListener("resize", function () {
      if (window.innerWidth > 880 && nav.classList.contains("is-open")) {
        toggleNav(false);
      }
    });
  }

  /* --------------------------------- 2. ヘッダーのスクロール状態 */
  var header = document.querySelector(".header");
  var toTop = document.querySelector(".to-top");

  var onScroll = function () {
    var y = window.pageYOffset || document.documentElement.scrollTop;
    if (header) header.classList.toggle("is-scrolled", y > 8);
    if (toTop) toTop.classList.toggle("is-visible", y > 480);
  };

  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  /* ---------------------------- 3. スクロールに応じたフェードイン */
  var targets = document.querySelectorAll(".reveal, .a-up, [data-anim=\"chars\"]");

  var show = function (el) {
    el.classList.add("is-in");
  };

  // 保険：すでに画面内へ来ている（または通り過ぎた）のに未表示の要素を表示する
  // （監視が届かない環境で、文字が隠れたままになるのを防ぐ）
  var showIfVisible = function () {
    targets.forEach(function (el) {
      if (el.classList.contains("is-in")) return;
      if (el.getBoundingClientRect().top < window.innerHeight * 0.95) show(el);
    });
  };

  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            show(entry.target);
            io.unobserve(entry.target);
          }
        });
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.08 }
    );
    targets.forEach(function (el) {
      io.observe(el);
    });
    window.setTimeout(showIfVisible, 1200);
    window.setTimeout(showIfVisible, 3000);
  } else {
    targets.forEach(show);
  }

  /* ------------------------------- 4. カテゴリー絞り込み（WORKS） */
  // data-filter-group="works" のボタン群が、同じグループの
  // data-category を持つ要素を絞り込みます。
  document.querySelectorAll("[data-filter-group]").forEach(function (group) {
    var name = group.getAttribute("data-filter-group");
    var items = document.querySelectorAll('[data-filter-target="' + name + '"]');
    var counter = document.querySelector('[data-filter-count="' + name + '"]');

    group.addEventListener("click", function (e) {
      var btn = e.target.closest(".filter__btn");
      if (!btn) return;

      var cat = btn.getAttribute("data-category") || "all";
      group.querySelectorAll(".filter__btn").forEach(function (b) {
        b.classList.toggle("is-active", b === btn);
        b.setAttribute("aria-pressed", String(b === btn));
      });

      var shown = 0;
      items.forEach(function (item) {
        var match =
          cat === "all" ||
          (item.getAttribute("data-category") || "").split(" ").indexOf(cat) >= 0;
        item.classList.toggle("is-hidden", !match);
        if (match) shown++;
      });

      if (counter) counter.textContent = shown;
    });
  });

  /* ------------------------------------ 5. ページトップへ戻るボタン */
  if (toTop) {
    toTop.addEventListener("click", function (e) {
      e.preventDefault();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  /* -------------------------------- 6. コピーライトの年号自動更新 */
  document.querySelectorAll("[data-year]").forEach(function (el) {
    el.textContent = String(new Date().getFullYear());
  });

  /* ------------------- 7. お問い合わせフォームの送信（メール作成） */
  // content.txt の [site] form_action: を設定した場合は、そのURLへ普通に送信されます
  // （この処理は動かず、data-mail-form も付きません）。
  // 空の場合は、入力内容から mailto: を組み立てて訪問者のメールソフトを開きます。
  var form = document.querySelector("[data-mail-form]");
  if (form) {
    var val = function (name) {
      var el = form.elements[name];
      return el && el.value ? el.value.trim() : "";
    };

    form.addEventListener("submit", function (e) {
      e.preventDefault();

      var to = form.getAttribute("data-mail-to");
      var msg = form.querySelector("[data-form-message]");
      if (!to) {                      // 送信先が未設定のときは案内だけ出す
        if (msg) {
          msg.hidden = false;
          msg.focus();
        }
        return;
      }

      if (!form.checkValidity()) {    // 必須項目のチェックはブラウザに任せる
        form.reportValidity();
        return;
      }

      var body = [
        "お名前: " + val("name"),
        "会社名・団体名: " + val("company"),
        "メールアドレス: " + val("email"),
        "お問い合わせ種別: " + val("type"),
        "",
        "お問い合わせ内容:",
        val("message"),
        ""
      ].join("\n");

      var subject = form.getAttribute("data-mail-subject") || "お問い合わせ";
      if (val("type")) {
        subject += " / " + val("type");
      }

      if (msg) {
        msg.hidden = false;
        msg.focus();
      }
      window.location.href =
        "mailto:" + to +
        "?subject=" + encodeURIComponent(subject) +
        "&body=" + encodeURIComponent(body);
    });
  }

  /* ------------------- 8. 見出しを1文字ずつに分割（文字アニメーション用） */
  // data-anim="chars" を付けた要素の文字を span で包み、
  // 1文字ごとに遅延（--i）を設定します。<em> などの入れ子は保ったままです。
  var splitChars = function (el, counter) {
    var nodes = Array.prototype.slice.call(el.childNodes);
    nodes.forEach(function (node) {
      if (node.nodeType === 3) {
        var frag = document.createDocumentFragment();
        node.nodeValue.split("").forEach(function (ch) {
          if (ch === " " || ch === "\n" || ch === "\t") {
            frag.appendChild(document.createTextNode(" "));
            return;
          }
          var s = document.createElement("span");
          s.className = "a-char";
          s.style.setProperty("--i", counter.n++);
          s.textContent = ch;
          frag.appendChild(s);
        });
        el.replaceChild(frag, node);
      } else if (node.nodeType === 1) {
        splitChars(node, counter);
      }
    });
  };

  document.querySelectorAll('[data-anim="chars"]').forEach(function (el) {
    // 読み上げは分割前の文章のままにする
    var label = el.textContent.replace(/\s+/g, " ").trim();
    if (label) el.setAttribute("aria-label", label);
    splitChars(el, { n: 0 });
  });

  /* --------------- 9. リンク・ボタンの文字をホバーで入れ替える準備 */
  // 文字を2枚重ねにして、CSS側で上下に入れ替えます（装飾のみ）。
  document.querySelectorAll(".nav__link, .btn, .filter__btn").forEach(function (el) {
    if (el.querySelector(".a-switch") || el.children.length) return;
    var text = el.textContent.trim();
    if (!text) return;

    var wrap = document.createElement("span");
    wrap.className = "a-switch";

    var front = document.createElement("span");
    front.textContent = text;

    var back = document.createElement("span");
    back.className = "dup";
    back.textContent = text;
    back.setAttribute("aria-hidden", "true");

    wrap.appendChild(front);
    wrap.appendChild(back);
    el.textContent = "";
    el.appendChild(wrap);
  });

  /* ------------------------- 10. 画像を押して詳細をポップアップ表示 */
  // カード内の .card__detail をポップアップへ複製して表示します。
  var modal = document.querySelector("[data-modal]");

  if (modal) {
    var mImg = modal.querySelector("[data-modal-image]");
    var mTags = modal.querySelector("[data-modal-tags]");
    var mTitle = modal.querySelector("[data-modal-title]");
    var mDetail = modal.querySelector("[data-modal-detail]");
    var opener = null;

    var fill = function (box, source) {
      box.textContent = "";
      if (!source) return;
      var clone = source.cloneNode(true);
      while (clone.firstChild) box.appendChild(clone.firstChild);
    };

    var openModal = function (button) {
      var card = button.closest(".card");
      if (!card) return;

      var thumb = button.querySelector("img");
      var title = card.querySelector(".card__title");

      if (thumb) {
        mImg.setAttribute("src", thumb.getAttribute("src"));
        mImg.setAttribute("width", thumb.getAttribute("width") || "");
        mImg.setAttribute("height", thumb.getAttribute("height") || "");
        mImg.setAttribute("alt", thumb.getAttribute("alt") || "");
      }
      mTitle.textContent = title ? title.textContent : "";
      fill(mTags, card.querySelector(".tag-row"));
      fill(mDetail, card.querySelector(".card__detail"));

      opener = button;
      if (typeof modal.showModal === "function") {
        modal.showModal();
      } else {
        modal.setAttribute("open", ""); // <dialog> 未対応環境
      }
      modal.scrollTop = 0;
      document.body.style.overflow = "hidden";
    };

    var closeModal = function () {
      if (typeof modal.close === "function") {
        modal.close();
      } else {
        modal.removeAttribute("open");
        document.body.style.overflow = "";
        if (opener) {
          opener.focus();
          opener = null;
        }
      }
    };

    document.addEventListener("click", function (e) {
      var opened = e.target.closest(".card__open");
      if (opened) {
        openModal(opened);
        return;
      }
      if (e.target.closest("[data-modal-close]")) {
        closeModal();
        return;
      }
      // ポップアップの外側（背景）を押したら閉じる
      if (e.target === modal) closeModal();
    });

    // ホームの写真タイルから works.html#works-01 のように来たときは、
    // その項目のポップアップを開く
    var openFromHash = function () {
      var id = window.location.hash.replace("#", "");
      if (!id) return;
      var card = document.getElementById(id);
      if (!card || !card.classList.contains("card")) return;
      var button = card.querySelector(".card__open");
      if (!button) return;
      card.scrollIntoView({ block: "center" });
      openModal(button);
    };

    openFromHash();
    window.addEventListener("hashchange", openFromHash);

    // Esc・閉じるボタンのどちらでも後片付けする
    modal.addEventListener("close", function () {
      document.body.style.overflow = "";
      if (opener) {
        opener.focus();
        opener = null;
      }
    });
  }

  /* ------------- 11. スライドカード（前後ボタン・カウンター・ドラッグ） */
  document.querySelectorAll("[data-slider]").forEach(function (slider) {
    var track = slider.querySelector("[data-slider-track]");
    if (!track) return;

    var items = track.children;
    var prev = slider.querySelector("[data-slider-prev]");
    var next = slider.querySelector("[data-slider-next]");
    var current = slider.querySelector("[data-slider-current]");
    var total = slider.querySelector("[data-slider-total]");

    if (total) total.textContent = items.length;
    if (items.length < 2) {
      var nav = slider.querySelector(".slider__nav");
      if (nav) nav.hidden = true;
      return;
    }

    // カード1枚分の移動量
    var step = function () {
      return items[1].offsetLeft - items[0].offsetLeft || track.clientWidth;
    };

    var indexNow = function () {
      return Math.round(track.scrollLeft / step());
    };

    var atStart = function () {
      return track.scrollLeft <= 2;
    };

    var atEnd = function () {
      return track.scrollLeft >= track.scrollWidth - track.clientWidth - 2;
    };

    var setCount = function (i) {
      if (!current) return;
      current.textContent = Math.min(items.length, Math.max(1, i + 1));
    };

    var goTo = function (i) {
      var max = items.length - 1;
      if (i < 0) i = 0;
      if (i > max) i = max;
      // スクロールイベントを待たずにカウンターを更新する
      setCount(i);
      track.scrollTo({ left: items[i].offsetLeft - items[0].offsetLeft });
    };

    // 指でのスワイプやドラッグに追従させる
    var update = function () {
      setCount(indexNow());
    };

    track.addEventListener("scroll", update, { passive: true });
    update();

    if (prev) {
      prev.addEventListener("click", function () {
        // 先頭で押したら末尾へ回る
        goTo(atStart() ? items.length - 1 : indexNow() - 1);
      });
    }

    if (next) {
      next.addEventListener("click", function () {
        // 最後まで来ていたら先頭へ戻る
        goTo(atEnd() ? 0 : indexNow() + 1);
      });
    }

    // マウスでのドラッグ移動（指はブラウザ標準のスクロールに任せる）
    var dragging = false;
    var moved = false;
    var startX = 0;
    var startLeft = 0;

    track.addEventListener("pointerdown", function (e) {
      if (e.pointerType !== "mouse" || e.button !== 0) return;
      dragging = true;
      moved = false;
      startX = e.clientX;
      startLeft = track.scrollLeft;
      track.classList.add("is-grabbing");
    });

    window.addEventListener("pointermove", function (e) {
      if (!dragging) return;
      var dx = e.clientX - startX;
      if (Math.abs(dx) > 6) moved = true;
      track.scrollLeft = startLeft - dx;
    });

    window.addEventListener("pointerup", function () {
      if (!dragging) return;
      dragging = false;
      track.classList.remove("is-grabbing");
      goTo(indexNow());
    });

    // ドラッグ後の指離しでリンクへ飛ばないようにする
    track.addEventListener(
      "click",
      function (e) {
        if (moved) {
          e.preventDefault();
          e.stopPropagation();
          moved = false;
        }
      },
      true
    );
  });
})();
