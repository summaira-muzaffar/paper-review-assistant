# Language plan, Paper Review Assistant

Date: 5 November 2026
Status: DECIDED by Summaira on 5 November 2026. Option 3: English main with Chinese toggle. The foundation was built and tested the same day: src/i18n.py holds 36 labels in both languages, and the sidebar language switch in app.py flips the interface between English and Chinese. See the addendum in BUILD_LOG.md for the test result.

## Current state

Step 1 is in English only. No language decision had been made before Summaira asked about it on 5 November 2026.

## The context

- Professor Tao is Chinese, at Northwestern Polytechnical University. His assessment document and his reply were in Chinese.
- Summaira's outreach to him was in English, and the master's she is seeking under the Chinese Government Scholarship is an international place, where English is the working language of study and of academic publishing.
- Summaira does not read Chinese. Everything in this project must stay explainable and checkable by her.

## Options checked

### Option 1, English only

Strengths: simplest, fastest, everything is fully checkable by Summaira, and English is the standard language for GitHub, for research papers, and for international programmes in China.
Weakness: it does not show any thought for the professor's own language, even though his task document was written in Chinese.

### Option 2, Fully bilingual, two complete versions

Strengths: looks thorough at first glance.
Weaknesses: doubles every label, help text, and document. Worse, Summaira could not read or verify half of her own project. If he asked one question about a Chinese sentence in her interface, she could not answer from her own knowledge. That risk is not worth it.

### Option 3, English first, with a Chinese interface toggle (recommended)

How it works:
- The app is built in English, which stays the main and default language.
- From Step 2 onward, every fixed interface label is stored in one language dictionary in the code, with an English text and a Chinese text for each label.
- A language switch in the sidebar lets the user flip the whole interface between English and Chinese at any time. Only fixed labels are translated, never user text and never the paper itself.
- In Step 5, a review language selector lets the user choose whether the generated review comes back in English or in Chinese. The LLM is instructed in the prompt to answer in the chosen language. Default stays English.
- In Step 8, the README stays in English, with one short Chinese summary paragraph near the top, translated from the English summary so Summaira knows exactly what it says.
- The submission email to Professor Tao stays in English.

Why this is the right balance:
- It shows respect and thought for his language, which is a genuine plus for a Chinese professor reading work from an international applicant.
- It is cheap to do if we design for it from Step 2. Retrofitting it later would cost much more, which is why the decision is needed now.
- It is safe for Summaira. The translated items are short, fixed labels, not free text she would have to defend sentence by sentence. She can explain the design in one sentence: the interface supports both languages because the tool is meant for international academic use.
- It is also a real feature, not decoration. A paper review tool used in a Chinese university would genuinely be used in both languages.

Cost: small. One dictionary file, one sidebar switch, and care at each step to add new labels to the dictionary instead of hard coding them.

## Recommendation

Option 3. English first, Chinese interface toggle, review output language selectable, one short Chinese summary in the README. No fully duplicated documents.
