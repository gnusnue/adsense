    function onlyDigits(value) {
      return (value || "").replace(/\D/g, "");
    }

    function parseYmdDate(yearText, monthText, dayText) {
      var yText = onlyDigits(yearText);
      var mText = onlyDigits(monthText);
      var dText = onlyDigits(dayText);
      if (yText.length !== 4 || mText.length !== 2 || dText.length !== 2) return null;
      var y = Number(yText);
      var m = Number(mText);
      var d = Number(dText);
      var dt = new Date(y, m - 1, d);
      if (dt.getFullYear() !== y || dt.getMonth() !== m - 1 || dt.getDate() !== d) {
        return null;
      }
      return dt;
    }

    function parseBirthDate(yearText, monthText, dayText) {
      return parseYmdDate(yearText, monthText, dayText);
    }

    function parseDate(value) {
      if (!value) return null;
      var match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
      if (!match) return null;
      var dt = new Date(value);
      if (Number.isNaN(dt.getTime())) return null;
      return new Date(dt.getFullYear(), dt.getMonth(), dt.getDate());
    }

    function bindDateYearLimit(el) {
      if (!el) return;
      el.setAttribute("min", "1000-01-01");
      el.setAttribute("max", "9999-12-31");

      var normalize = function () {
        var value = el.value || "";
        if (!value) {
          el.setCustomValidity("");
          return;
        }
        var parts = value.split("-");
        if (parts.length !== 3) return;

        var year = onlyDigits(parts[0]);
        var month = onlyDigits(parts[1]).slice(0, 2);
        var day = onlyDigits(parts[2]).slice(0, 2);
        if (year.length > 4) year = year.slice(0, 4);

        if (year.length === 4 && month.length === 2 && day.length === 2) {
          var normalized = year + "-" + month + "-" + day;
          if (normalized !== value) el.value = normalized;
          el.setCustomValidity("");
          return;
        }

        if (year.length > 0 && year.length !== 4) {
          el.setCustomValidity("연도는 4자리만 입력하세요.");
          return;
        }
        el.setCustomValidity("");
      };

      el.addEventListener("input", normalize);
      el.addEventListener("change", normalize);
    }

    function daysBetween(start, end) {
      var ms = 24 * 60 * 60 * 1000;
      return Math.floor((end - start) / ms) + 1;
    }

    function ageAtDate(birthDate, referenceDate) {
      var age = referenceDate.getFullYear() - birthDate.getFullYear();
      var monthDiff = referenceDate.getMonth() - birthDate.getMonth();
      if (monthDiff < 0 || (monthDiff === 0 && referenceDate.getDate() < birthDate.getDate())) {
        age -= 1;
      }
      return age;
    }

    function getBenefitDays(age, tenureDays) {
      var years = tenureDays / 365;
      var isSenior = age >= 50;
      if (years < 1) return 120;
      if (years < 3) return isSenior ? 180 : 150;
      if (years < 5) return isSenior ? 210 : 180;
      if (years < 10) return isSenior ? 240 : 210;
      return isSenior ? 270 : 240;
    }

    function formatWon(value) {
      if (!Number.isFinite(value)) return "-";
      return Math.round(value).toLocaleString("ko-KR") + "원";
    }

    function formatNumber(value) {
      if (!Number.isFinite(value)) return "0";
      return Math.round(value).toLocaleString("ko-KR");
    }

    function daysInLast3Months(endDate) {
      var startDate = new Date(endDate);
      startDate.setMonth(startDate.getMonth() - 3);
      var ms = 24 * 60 * 60 * 1000;
      return Math.max(1, Math.floor((endDate - startDate) / ms));
    }

    function parseMonthlyAmount(value) {
      var digits = onlyDigits(value || "");
      if (!digits) return 0;
      var parsed = Number(digits);
      if (!Number.isFinite(parsed)) return 0;
      return parsed;
    }

    function trackEvent(name, params) {
      if (typeof window.gtag !== "function") return;
      window.gtag("event", name, params || {});
    }

    function formatKoreanAmountParts(amount) {
      if (!Number.isFinite(amount) || amount <= 0) return "";

      var eok = Math.floor(amount / 100000000);
      var afterEok = amount % 100000000;
      var man = Math.floor(afterEok / 10000);
      var rest = afterEok % 10000;
      var parts = [];

      if (eok > 0) {
        parts.push(eok.toLocaleString("ko-KR") + "억");
      }
      if (man > 0) {
        parts.push(man.toLocaleString("ko-KR") + "만");
      }
      if (rest > 0) {
        parts.push(rest.toLocaleString("ko-KR"));
      }

      if (parts.length === 0) {
        return amount.toLocaleString("ko-KR");
      }
      return parts.join(" ");
    }

    function getMonthlyUnitText(amount) {
      if (!amount || amount <= 0) return "숫자를 입력하면 단위가 자동 반영됩니다.";
      return formatKoreanAmountParts(amount);
    }

    function getMinWageByYear(year) {
      var table = {
        2011: 4320,
        2012: 4580,
        2013: 4860,
        2014: 5210,
        2015: 5580,
        2016: 6030,
        2017: 6470,
        2018: 7530,
        2019: 8350,
        2020: 8590,
        2021: 8720,
        2022: 9160,
        2023: 9620,
        2024: 9860,
        2025: 10030,
        2026: 10320
      };
      if (table[year]) return table[year];
      if (year > 2026) return table[2026];
      return 0;
    }

    function bindBirthSegment(el, maxLen, nextEl, prevEl) {
      if (!el) return;
      el.addEventListener("input", function () {
        var digits = onlyDigits(el.value).slice(0, maxLen);
        el.value = digits;
        if (digits.length === maxLen && nextEl) {
          nextEl.focus();
        }
      });
      el.addEventListener("keydown", function (event) {
        if (event.key === "Backspace" && el.value.length === 0 && prevEl) {
          prevEl.focus();
        }
      });
    }

    function renderPaymentSchedule(daily, benefitDays) {
      var container = document.getElementById("paymentSchedule");
      var remaining = benefitDays;
      var round = 1;
      var items = [];

      while (remaining > 0) {
        var dayCount = Math.min(30, remaining);
        var amount = daily * dayCount;
        items.push(
          '<div class="text-center p-4 rounded-xl border border-slate-100">' +
            '<div class="w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center text-xs font-bold mx-auto mb-3">' + round + '회</div>' +
            '<p class="text-sm font-bold mb-1">' + formatWon(amount) + '</p>' +
            '<p class="text-[10px] text-slate-400">' + dayCount + '일분</p>' +
          '</div>'
        );
        remaining -= dayCount;
        round += 1;
      }

      container.innerHTML = items.join("");
    }

    var birthYearInput = document.getElementById("birthYear");
    var birthMonthInput = document.getElementById("birthMonth");
    var birthDayInput = document.getElementById("birthDay");
    var startInput = document.getElementById("start");
    var endInput = document.getElementById("end");
    var monthlyInput = document.getElementById("monthly");
    var monthlyUnitHint = document.getElementById("monthlyUnitHint");
    bindBirthSegment(birthYearInput, 4, birthMonthInput, null);
    bindBirthSegment(birthMonthInput, 2, birthDayInput, birthYearInput);
    bindBirthSegment(birthDayInput, 2, null, birthMonthInput);
    bindDateYearLimit(startInput);
    bindDateYearLimit(endInput);

    function refreshMonthlyHint() {
      var amount = parseMonthlyAmount(monthlyInput.value);
      monthlyUnitHint.textContent = getMonthlyUnitText(amount);
    }

    monthlyInput.addEventListener("input", function () {
      var digits = onlyDigits(monthlyInput.value).slice(0, 13);
      monthlyInput.value = digits ? Number(digits).toLocaleString("ko-KR") : "";
      refreshMonthlyHint();
    });
    refreshMonthlyHint();

    document.getElementById("calcBtn").addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      trackEvent("calc_submit", { event_category: "engagement", event_label: "home_calculator" });

      var birthDate = parseBirthDate(
        birthYearInput.value,
        birthMonthInput.value,
        birthDayInput.value
      );
      var start = parseDate(startInput.value);
      var end = parseDate(endInput.value);
      var monthly = parseMonthlyAmount(monthlyInput.value);

      if (!birthDate || !start || !end || monthly <= 0) {
        alert("생년월일(YYYY/MM/DD), 입사일, 퇴사일, 월급을 입력하세요.");
        return;
      }
      if (end < start) {
        alert("퇴사일은 입사일 이후여야 합니다.");
        return;
      }

      var age = ageAtDate(birthDate, end);
      if (age < 0 || age > 100) {
        alert("생년월일 형식을 확인하세요.");
        return;
      }

      var tenureDays = Math.max(1, daysBetween(start, end));
      var benefitDays = getBenefitDays(age, tenureDays);
      var last3MonthsDays = daysInLast3Months(end);
      var avgDaily = (monthly * 3) / last3MonthsDays;
      var daily = avgDaily * 0.6;

      var endYear = end.getFullYear();
      var cap = endYear >= 2026 ? 68100 : 66000;
      var minWage = getMinWageByYear(endYear);
      var floor = minWage > 0 ? minWage * 8 * 0.8 : 0;

      daily = Math.min(daily, cap);
      if (floor > 0) {
        daily = Math.max(daily, floor);
      }

      var total = daily * benefitDays;
      var years = Math.floor(tenureDays / 365);
      var months = Math.floor((tenureDays % 365) / 30);

      document.getElementById("daily").textContent = formatWon(daily);
      document.getElementById("days").textContent = benefitDays.toLocaleString("ko-KR") + "일";
      document.getElementById("tenure").textContent = years + "년 " + months + "개월";
      document.getElementById("total").textContent = formatNumber(total);
      renderPaymentSchedule(daily, benefitDays);

      var resultSection = document.getElementById("calcResultSection");
      resultSection.classList.remove("hidden");
      trackEvent("calc_result_view", {
        event_category: "engagement",
        benefit_days: benefitDays,
        total_amount: Math.round(total)
      });
      resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
    });

    document.getElementById("resetBtn").addEventListener("click", function (event) {
      event.preventDefault();
      birthYearInput.value = "";
      birthMonthInput.value = "";
      birthDayInput.value = "";
      startInput.value = "";
      endInput.value = "";
      monthlyInput.value = "";
      refreshMonthlyHint();
      document.getElementById("calcResultSection").classList.add("hidden");
      birthYearInput.focus();
    });

    var applyNowLink = document.getElementById("applyNowLink");
    if (applyNowLink) {
      applyNowLink.addEventListener("click", function () {
        trackEvent("cta_apply_click", { event_category: "conversion", event_label: "calc_result_apply" });
      });
    }
