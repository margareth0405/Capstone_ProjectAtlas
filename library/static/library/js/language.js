(function () {
  "use strict";

  var translations = {
    "Skip to main content": "Lumaktaw sa pangunahing nilalaman",
    "Display": "Ayos",
    "Display settings": "Mga setting ng pagpapakita",
    "Choose the reading style that is most comfortable for you.": "Piliin ang istilo ng pagbasa na pinakakomportable para sa iyo.",
    "Reading preferences": "Mga kagustuhan sa pagbasa",
    "Color theme": "Tema ng kulay",
    "Light mode": "Maliwanag na mode",
    "Dark mode": "Madilim na mode",
    "Large text": "Malaking teksto",
    "High contrast": "Mataas na contrast",
    "Loading ATLAS": "Nilo-load ang ATLAS",
    "Confirm action": "Kumpirmahin ang aksyon",
    "Cancel": "Kanselahin",
    "Continue": "Magpatuloy",
    "Digital Sources": "Mga Digital na Sanggunian",
    "DIGITAL SOURCES": "MGA DIGITAL NA SANGGUNIAN",
    "Home": "Home",
    "HOME": "HOME",
    "Contact": "Makipag-ugnayan",
    "CONTACT": "MAKIPAG-UGNAYAN",
    "Privacy & Terms": "Privacy at Mga Tuntunin",
    "Cookie preferences": "Mga kagustuhan sa cookie",
    "Footer navigation": "Nabigasyon sa ibaba",
    "Support contact details": "Mga detalye sa pakikipag-ugnayan para sa suporta",
    "Close cookie preferences": "Isara ang mga kagustuhan sa cookie",
    "Read the cookie policy": "Basahin ang patakaran sa cookie",
    "Essential only": "Mahalagang cookies lamang",
    "Allow analytics": "Payagan ang analytics",
    "ATLAS always uses essential security and session cookies and records signed-in account activity for Digital Sources administration. With your permission, it also records privacy-conscious guest usage statistics.": "Palaging gumagamit ang ATLAS ng mahahalagang security at session cookie at nagtatala ng aktibidad ng naka-sign in na account para sa pamamahala ng Mga Digital na Sanggunian. Kapag pinahintulutan mo, nagtatala rin ito ng limitadong estadistika ng paggamit ng bisita.",

    "Academic Teaching, Learning, and Archival System": "Sistemang Akademiko para sa Pagtuturo, Pagkatuto, at Pag-archive",
    "Choose how you would like to continue.": "Piliin kung paano mo gustong magpatuloy.",
    "Student": "Mag-aaral",
    "Teacher": "Guro",
    "Guest": "Bisita",
    "Already have an account?": "May account ka na?",
    "Sign in": "Mag-sign in",
    "ATLAS asks registered users to accept its": "Hinihiling ng ATLAS sa mga rehistradong user na tanggapin ang",
    "Privacy Policy and Terms & Conditions": "Patakaran sa Privacy at Mga Tuntunin at Kondisyon",
    "before access.": "bago makagamit.",

    "Back": "Bumalik",
    "Back to login": "Bumalik sa pag-sign in",
    "Back to sign in": "Bumalik sa pag-sign in",
    "Choose account type": "Piliin ang uri ng account",
    "Student account": "Account ng mag-aaral",
    "Teacher account": "Account ng guro",
    "Student Login": "Pag-sign in ng Mag-aaral",
    "Teacher Login": "Pag-sign in ng Guro",
    "Student Registration": "Pagrehistro ng Mag-aaral",
    "Teacher Registration": "Pagrehistro ng Guro",
    "Access your ATLAS reading dashboard": "Buksan ang iyong ATLAS reading dashboard",
    "Create your secure ATLAS reading account.": "Gumawa ng ligtas na ATLAS reading account.",
    "Email": "Email",
    "DepEd email": "DepEd email",
    "Password": "Password",
    "Confirm password": "Kumpirmahin ang password",
    "Full name": "Buong pangalan",
    "Show password": "Ipakita ang password",
    "Show confirmation password": "Ipakita ang pagkumpirma ng password",
    "Teacher sign-in accepts official @deped.gov.ph accounts only.": "Opisyal na @deped.gov.ph account lamang ang tinatanggap para sa pag-sign in ng guro.",
    "Teachers must use an official @deped.gov.ph email address. Gmail addresses are not accepted.": "Kailangang gumamit ang mga guro ng opisyal na @deped.gov.ph email address. Hindi tinatanggap ang Gmail address.",
    "Use an active email address that you can open for verification.": "Gumamit ng aktibong email address na mabubuksan mo para sa beripikasyon.",
    "Use your current password. Previously created passwords still work; every new, reset, or changed password must contain at least 12 characters.": "Gamitin ang kasalukuyan mong password. Gumagana pa rin ang mga dating password; ang bawat bago, ni-reset, o binagong password ay kailangang may hindi bababa sa 12 character.",
    "Enter the same password again.": "Ilagay muli ang parehong password.",
    "Your password must include:": "Dapat kasama sa iyong password ang:",
    "At least 12 characters": "Hindi bababa sa 12 character",
    "At least one number": "Hindi bababa sa isang numero",
    "At least one symbol or punctuation character (any one is accepted)": "Hindi bababa sa isang simbolo o bantas (anumang isa ay tinatanggap)",
    "Both password fields match": "Magkapareho ang dalawang password",
    "Password strength": "Lakas ng password",
    "Strength:": "Lakas:",
    "Not entered": "Hindi pa nailalagay",
    "Weak": "Mahina",
    "Fair": "Katamtaman",
    "Strong": "Malakas",
    "I agree to keep the information I access through ATLAS private and accept the": "Sumasang-ayon akong panatilihing pribado ang impormasyong ina-access ko sa ATLAS at tinatanggap ko ang",
    "I confirm that I am legally able to consent, or that my parent or legal guardian has authorized this account and reviewed the": "Kinukumpirma kong maaari akong legal na pumayag, o pinahintulutan ng aking magulang o legal na tagapag-alaga ang account na ito at sinuri ang",
    "Review age and guardian confirmation": "Suriin ang kumpirmasyon sa edad at tagapag-alaga",
    "Review privacy agreement": "Suriin ang kasunduan sa privacy",
    "Review message privacy agreement": "Suriin ang kasunduan sa privacy ng mensahe",
    "View": "Tingnan",
    "Yes": "Oo",
    "I confirm and want to continue.": "Kinukumpirma ko at nais kong magpatuloy.",
    "I agree and want to continue.": "Sumasang-ayon ako at nais kong magpatuloy.",
    "I agree and want to send this message.": "Sumasang-ayon ako at nais kong ipadala ang mensaheng ito.",
    "privacy notice for minors": "abiso sa privacy para sa mga menor de edad",
    "Forgot your password?": "Nakalimutan ang iyong password?",
    "New student or teacher?": "Bagong mag-aaral o guro?",
    "Create an account": "Gumawa ng account",
    "Already registered?": "Rehistrado na?",
    "ATLAS will send a verification link to your email after registration.": "Magpapadala ang ATLAS ng verification link sa iyong email pagkatapos magrehistro.",

    "Digital Sources | ATLAS": "Mga Digital na Sanggunian | ATLAS",
    "Sign In | ATLAS": "Mag-sign In | ATLAS",
    "Create an Account | ATLAS": "Gumawa ng Account | ATLAS",
    "Reset Password | ATLAS": "I-reset ang Password | ATLAS",
    "Check Your Email | ATLAS": "Tingnan ang Iyong Email | ATLAS",
    "Confirm Email | ATLAS": "Kumpirmahin ang Email | ATLAS",
    "Choose a New Password | ATLAS": "Pumili ng Bagong Password | ATLAS",
    "Password Updated | ATLAS": "Na-update ang Password | ATLAS",

    "Reset your password": "I-reset ang iyong password",
    "Enter your account email and ATLAS will send you a secure reset link.": "Ilagay ang email ng iyong account at magpapadala ang ATLAS ng ligtas na reset link.",
    "Send reset link": "Ipadala ang reset link",
    "Check your email": "Tingnan ang iyong email",
    "If an ATLAS account matches that address, a password-reset link has been sent. Check your spam folder if it does not arrive shortly.": "Kung may ATLAS account na tumutugma sa address na iyon, naipadala na ang link sa pag-reset ng password. Tingnan ang spam folder kung hindi ito dumating agad.",
    "Send another reset link": "Magpadala ng panibagong reset link",
    "Return to sign in": "Bumalik sa pag-sign in",
    "Verify your email": "I-verify ang iyong email",
    "ATLAS sent a verification link to your email address. Open it to confirm your account. Check your spam folder if needed.": "Nagpadala ang ATLAS ng verification link sa iyong email address. Buksan ito upang kumpirmahin ang iyong account. Tingnan din ang spam folder kung kinakailangan.",
    "Already verified?": "Na-verify na?",
    "Confirm your email": "Kumpirmahin ang iyong email",
    "Verify email": "I-verify ang email",
    "This verification link is invalid or has expired.": "Hindi wasto o nag-expire na ang verification link na ito.",
    "Confirm": "Kumpirmahin",
    "as the email address for your ATLAS account.": "bilang email address ng iyong ATLAS account.",
    "This email address cannot be confirmed because it is already associated with another account.": "Hindi makumpirma ang email address na ito dahil nakaugnay na ito sa ibang account.",
    "Email verification required": "Kailangang i-verify ang email",
    "Verify your email address before signing in. ATLAS has sent you a new verification link.": "I-verify ang iyong email address bago mag-sign in. Nagpadala ang ATLAS ng bagong verification link.",
    "Reset link expired": "Nag-expire ang reset link",
    "This password-reset link is invalid or has already been used.": "Hindi wasto o nagamit na ang password-reset link na ito.",
    "Request a new link": "Humiling ng bagong link",
    "Choose a new password": "Pumili ng bagong password",
    "New password": "Bagong password",
    "Update password": "I-update ang password",
    "Password updated": "Na-update ang password",
    "Your new password is active. You can now sign in to ATLAS.": "Aktibo na ang bago mong password. Maaari ka nang mag-sign in sa ATLAS.",
    "Continue to sign in": "Magpatuloy sa pag-sign in",
    "Account settings": "Mga setting ng account",
    "Review your account identity and email verification status.": "Suriin ang pagkakakilanlan ng iyong account at status ng email verification.",
    "Email status": "Status ng email",
    "Verified": "Beripikado",
    "Not verified": "Hindi beripikado",
    "Resend verification email": "Ipadala muli ang verification email",
    "Teacher display name": "Pangalang ipinapakita ng guro",
    "Choose the name shown in your dashboard welcome message and account menu.": "Piliin ang pangalang makikita sa welcome message ng dashboard at account menu.",
    "Display name": "Pangalang ipapakita",
    "Save display name": "I-save ang pangalan",
    "Return to dashboard": "Bumalik sa dashboard",

    "Primary navigation": "Pangunahing nabigasyon",
    "ATLAS dashboard": "ATLAS dashboard",
    "Close navigation menu": "Isara ang menu ng nabigasyon",
    "BOOKMARKS": "MGA BOOKMARK",
    "USERS": "MGA USER",
    "AI DETECTION": "AI DETECTION",
    "ANNOUNCEMENTS": "MGA ANUNSYO",
    "knowledge for everyone": "kaalaman para sa lahat",
    "Open navigation menu": "Buksan ang menu ng nabigasyon",
    "MENU": "MENU",
    "Open account menu": "Buksan ang menu ng account",
    "ADMINISTRATOR": "ADMINISTRATOR",
    "TEACHER": "GURO",
    "GUEST": "BISITA",
    "STUDENT": "MAG-AARAL",
    "Account options": "Mga opsyon ng account",
    "Sign out": "Mag-sign out",
    "Breadcrumb": "Breadcrumb",
    "Dashboard": "Dashboard",
    "Scroll to top": "Bumalik sa itaas",

    "DISCOVER · READ · LEARN": "TUKLASIN · BASAHIN · MATUTO",
    "Welcome to": "Maligayang pagdating sa",
    "Digital Sources summary": "Buod ng Mga Digital na Sanggunian",
    "Digital Items": "Mga Digital na Item",
    "Collection Types": "Mga Uri ng Koleksyon",
    "Total Pages": "Kabuuang Pahina",
    "Unique Authors": "Mga Natatanging May-akda",
    "Quick actions": "Mabilis na aksyon",
    "Browse Digital Sources": "Mag-browse ng Mga Digital na Sanggunian",
    "New Arrivals": "Mga Bagong Dating",
    "Add Resource": "Magdagdag ng Sanggunian",
    "AI Detection": "AI Detection",
    "My Bookmarks": "Aking Mga Bookmark",
    "Recently Added": "Kamakailang Idinagdag",
    "View all": "Tingnan lahat",
    "Hard copy available": "May hard copy",
    "Hard copy unavailable": "Walang hard copy",
    "No resources yet": "Wala pang sanggunian",
    "Newly added resources will appear here.": "Dito lalabas ang mga bagong idinagdag na sanggunian.",
    "Latest Digital Sources Updates": "Pinakabagong Update sa Mga Digital na Sanggunian",
    "Administrator activity": "Aktibidad ng administrator",

    "ATLAS catalog": "Katalogo ng ATLAS",
    "Total Items:": "Kabuuang Item:",
    "Add resource": "Magdagdag ng sanggunian",
    "Latest announcements": "Pinakabagong mga anunsyo",
    "You are browsing as a guest. You can read protected resources in ATLAS.": "Nagba-browse ka bilang bisita. Maaari mong basahin ang mga protektadong sanggunian sa ATLAS.",
    "as a student or teacher to use bookmarks.": "bilang mag-aaral o guro upang gumamit ng mga bookmark.",
    "Student access: protected reading and bookmarks.": "Access ng mag-aaral: protektadong pagbasa at mga bookmark.",
    "Collection type": "Uri ng koleksyon",
    "All types": "Lahat ng uri",
    "Search Digital Sources": "Maghanap sa Mga Digital na Sanggunian",
    "Sort by": "Ayusin ayon sa",
    "Clear filters": "Alisin ang mga filter",
    "No cover image available": "Walang available na larawan ng cover",
    "No cover": "Walang cover",
    "No abstract has been provided.": "Walang ibinigay na abstract.",
    "Published": "Nai-publish",
    "Added to ATLAS": "Idinagdag sa ATLAS",
    "View abstract": "Tingnan ang abstract",
    "Read resource abstract": "Basahin ang abstract ng sanggunian",
    "Bookmarked": "Naka-bookmark",
    "Bookmark": "I-bookmark",
    "Edit": "I-edit",
    "Delete": "Tanggalin",
    "No resources found": "Walang nahanap na sanggunian",
    "Try a different search or collection filter.": "Sumubok ng ibang paghahanap o filter ng koleksyon.",

    "Announcements": "Mga Anunsyo",
    "Digital Sources updates": "Mga update sa Digital na Sanggunian",
    "New announcement": "Bagong anunsyo",
    "Category": "Kategorya",
    "All categories": "Lahat ng kategorya",
    "Reset": "I-reset",
    "All announcements": "Lahat ng anunsyo",
    "Review announcements": "Suriin ang mga anunsyo",
    "Draft": "Draft",
    "Saved": "Na-save",
    "Share": "Ibahagi",
    "Copy": "Kopyahin",
    "No announcements found": "Walang nahanap na anunsyo",
    "Published updates will appear here.": "Dito lalabas ang mga nai-publish na update.",

    "Contact Us": "Makipag-ugnayan sa Amin",
    "Support": "Suporta",
    "Contact methods": "Mga paraan ng pakikipag-ugnayan",
    "Support hours": "Oras ng suporta",
    "Phone": "Telepono",
    "Send a message": "Magpadala ng mensahe",
    "How can we help?": "Paano kami makatutulong?",
    "Name": "Pangalan",
    "What do you need?": "Ano ang kailangan mo?",
    "Subject": "Paksa",
    "Message": "Mensahe",
    "Send message": "Ipadala ang mensahe",

    "Your reading list": "Iyong listahan ng babasahin",
    "Bookmarks": "Mga Bookmark",
    "No bookmarks yet": "Wala pang bookmark",
    "Choose “Bookmark” beside any Digital Sources item to save it here.": "Piliin ang “I-bookmark” sa tabi ng anumang item sa Mga Digital na Sanggunian upang i-save ito rito.",
    "View details": "Tingnan ang mga detalye",
    "Back to Digital Sources": "Bumalik sa Mga Digital na Sanggunian",
    "Cover": "Cover",
    "Call number": "Call number",
    "Format": "Format",
    "Pages": "Mga pahina",
    "Physical access": "Pisikal na access",
    "Description or abstract": "Paglalarawan o abstract",
    "No description or abstract is available for this resource.": "Walang available na paglalarawan o abstract para sa sangguniang ito.",
    "Remove bookmark": "Alisin ang bookmark",
    "Edit resource": "I-edit ang sanggunian",

    "Privacy controls": "Mga kontrol sa privacy",
    "Choose whether ATLAS may collect optional, first-party guest usage statistics.": "Piliin kung maaaring mangolekta ang ATLAS ng opsyonal na estadistika ng paggamit ng bisita.",
    "Your current choice": "Kasalukuyan mong pinili",
    "Analytics allowed.": "Pinapayagan ang analytics.",
    "Essential cookies only.": "Mahahalagang cookie lamang.",
    "No optional cookie choice has been saved yet.": "Wala pang naka-save na opsyonal na pagpili sa cookie.",
    "Use essential only": "Gamitin lamang ang mahahalagang cookie",
    "Read the complete cookie policy": "Basahin ang buong patakaran sa cookie"
  };

  var attributeNames = ["aria-label", "placeholder", "title"];
  var originalText = new WeakMap();
  var originalAttributes = new WeakMap();

  function translatePhrase(value) {
    if (Object.prototype.hasOwnProperty.call(translations, value)) {
      return translations[value];
    }

    var match = value.match(/^Welcome,\s*(.+)$/);
    if (match) return "Maligayang pagdating, " + match[1];
    match = value.match(/^(\d+)\s+items?$/);
    if (match) return match[1] + " item";
    match = value.match(/^(\d+)\s+total$/);
    if (match) return match[1] + " kabuuan";
    match = value.match(/^View details for\s+(.+)$/);
    if (match) return "Tingnan ang mga detalye ng " + match[1];
    match = value.match(/^Remove\s+(.+)\s+from bookmarks$/);
    if (match) return "Alisin ang " + match[1] + " sa mga bookmark";
    return value;
  }

  function splitWhitespace(value) {
    var match = value.match(/^(\s*)(.*?)(\s*)$/s);
    return match || [value, "", value, ""];
  }

  function shouldSkip(node) {
    var parent = node.nodeType === Node.TEXT_NODE ? node.parentElement : node;
    return !parent || Boolean(parent.closest(
      "script, style, code, pre, textarea, [data-no-translate], [data-language-choice]"
    ));
  }

  function applyText(node, language) {
    if (shouldSkip(node)) return;
    if (!originalText.has(node)) originalText.set(node, node.nodeValue);
    var source = originalText.get(node);
    if (language === "en") {
      if (node.nodeValue !== source) node.nodeValue = source;
      return;
    }
    var parts = splitWhitespace(source);
    var translated = parts[1] + translatePhrase(parts[2]) + parts[3];
    if (node.nodeValue !== translated) node.nodeValue = translated;
  }

  function applyAttributes(element, language) {
    if (shouldSkip(element)) return;
    var saved = originalAttributes.get(element);
    if (!saved) {
      saved = {};
      attributeNames.forEach(function (name) {
        if (element.hasAttribute(name)) saved[name] = element.getAttribute(name);
      });
      originalAttributes.set(element, saved);
    }
    Object.keys(saved).forEach(function (name) {
      var value = language === "fil" ? translatePhrase(saved[name]) : saved[name];
      if (element.getAttribute(name) !== value) element.setAttribute(name, value);
    });
  }

  class AtlasLanguagePreference {
    constructor() {
      this.storageKey = "atlas_language";
      this.language = this.read();
      this.observer = null;
    }

    read() {
      try {
        return window.localStorage.getItem(this.storageKey) === "fil" ? "fil" : "en";
      } catch (error) {
        return "en";
      }
    }

    save() {
      try {
        window.localStorage.setItem(this.storageKey, this.language);
      } catch (error) {
        // The selected language still applies to the current page.
      }
    }

    apply(root) {
      var target = root || document.body;
      if (!target) return;
      document.documentElement.lang = this.language === "fil" ? "fil" : "en";

      if (target.nodeType === Node.TEXT_NODE) {
        applyText(target, this.language);
      } else {
        applyAttributes(target, this.language);
        var walker = document.createTreeWalker(
          target,
          NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT
        );
        var current = walker.nextNode();
        while (current) {
          if (current.nodeType === Node.TEXT_NODE) {
            applyText(current, this.language);
          } else {
            applyAttributes(current, this.language);
          }
          current = walker.nextNode();
        }
      }
      this.syncButtons();
    }

    syncButtons() {
      var selected = this.language;
      document.querySelectorAll("[data-language-choice]").forEach(function (button) {
        button.setAttribute(
          "aria-pressed",
          String(button.dataset.languageChoice === selected)
        );
      });
    }

    setLanguage(language) {
      this.language = language === "fil" ? "fil" : "en";
      this.save();
      this.apply(document.documentElement);
    }

    initialize() {
      var self = this;
      document.querySelectorAll("[data-language-choice]").forEach(function (button) {
        button.addEventListener("click", function () {
          self.setLanguage(button.dataset.languageChoice);
        });
      });
      this.apply(document.body);
      this.observer = new MutationObserver(function (mutations) {
        if (self.language !== "fil") return;
        mutations.forEach(function (mutation) {
          if (mutation.type === "characterData") self.apply(mutation.target);
          mutation.addedNodes.forEach(function (node) {
            self.apply(node);
          });
        });
      });
      this.observer.observe(document.body, { childList: true, characterData: true, subtree: true });
    }
  }

  var languagePreference = new AtlasLanguagePreference();
  languagePreference.initialize();
  window.AtlasLanguage = languagePreference;
}());
