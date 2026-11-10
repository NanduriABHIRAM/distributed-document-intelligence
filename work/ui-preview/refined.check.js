
  (() => {
    const $ = id => document.getElementById(id);
    const pages = ['overview', 'ask', 'library', 'evidence'];
    const docs = [
      { name: 'Operating Systems — Introduction', path: 'samples/operating-systems.pdf', type: 'PDF', chunks: 3 },
      { name: 'Process Scheduling', path: 'samples/process-scheduling.pdf', type: 'PDF', chunks: 3 },
      { name: 'Database Fundamentals', path: 'samples/database-fundamentals.pdf', type: 'PDF', chunks: 3 }
    ];
    const samples = [
      { match: /operating|\bos\b/i, query: 'What is an operating system?', doc: docs[0], answer: 'An operating system manages the computer’s hardware and provides services for applications. It coordinates processor time, memory, files, and input/output devices.', passages: ['An operating system manages the computer’s hardware and provides services for applications.', 'It coordinates processor time, memory, files, and input/output devices.', 'Applications use operating system services to access shared computing resources.'] },
      { match: /process|schedul/i, query: 'Explain process scheduling', doc: docs[1], answer: 'Process scheduling selects a ready process to run on the CPU. The scheduler uses a policy to allocate processor time among competing processes.', passages: ['Process scheduling selects a ready process to run on the CPU.', 'The scheduler uses a policy to allocate processor time among competing processes.', 'Round-robin scheduling assigns each process a limited time slice before another ready process runs.'] },
      { match: /normal|database|dbms/i, query: 'What is normalization in DBMS?', doc: docs[2], answer: 'Normalization organizes database tables to reduce redundant data. Separating related facts can help prevent insertion, update, and deletion anomalies.', passages: ['Normalization organizes database tables to reduce redundant data.', 'Separating related facts can help prevent insertion, update, and deletion anomalies.', 'A table in first normal form contains a single value in each cell.'] }
    ];
    function escape(text) { const el = document.createElement('span'); el.textContent = text; return el.innerHTML; }
    function showPage(page) {
      if (!pages.includes(page)) return;
      pages.forEach(id => { $(id).hidden = id !== page; });
      document.querySelectorAll('.nav-link').forEach(button => {
        const active = button.dataset.page === page;
        button.classList.toggle('active', active);
        if (active) button.setAttribute('aria-current', 'page'); else button.removeAttribute('aria-current');
      });
      $('announcement').textContent = page === 'ask' ? 'Ask Documents' : page === 'library' ? 'Document Library' : page === 'evidence' ? 'Evidence Explorer' : 'Overview';
    }
    document.querySelectorAll('[data-page]').forEach(button => button.addEventListener('click', () => showPage(button.dataset.page)));
    function theme(dark) {
      document.documentElement.dataset.theme = dark ? 'dark' : 'light';
      $('theme').textContent = dark ? 'Light mode' : 'Dark mode';
      $('theme').setAttribute('aria-pressed', String(dark));
    }
    try { theme(localStorage.getItem('tracerag-design-theme') === 'dark'); } catch (_) { theme(false); }
    $('theme').addEventListener('click', () => {
      const dark = document.documentElement.dataset.theme !== 'dark';
      theme(dark);
      try { localStorage.setItem('tracerag-design-theme', dark ? 'dark' : 'light'); } catch (_) {}
    });
    function evidenceGrid(sample, prefix) {
      return `<div class="evidence-header"><h3>Supporting evidence <span> / 3</span></h3><p>Sample source passages</p></div><div class="evidence-grid">${sample.passages.map((text, i) => `<article class="evidence-card" id="${prefix}-${i}"><div class="evidence-top"><span class="citation">[E${i + 1}]</span><span>Passage ${i + 1}</span></div><h4>${escape(sample.doc.name)}</h4><div class="source-line">PDF &nbsp; / &nbsp; PAGE ${i + 2}</div><p class="clamp">${escape(text)}</p><div class="source-detail" hidden><p class="source-line">${escape(sample.doc.path)}<br>Chunk: sample-${samples.indexOf(sample) + 1}-${i + 1}</p></div><button type="button" class="read-evidence" aria-expanded="false">Read evidence ↗</button></article>`).join('')}</div>`;
    }
    function run() {
      const query = $('question').value.trim();
      const sample = samples.find(item => item.match.test(query));
      $('ask-empty').hidden = true;
      $('result').hidden = false;
      if (!sample) {
        $('result').innerHTML = '<section class="empty-state"><h3>This question is outside the demo samples.</h3><p>Choose one of the three example questions above. This preview does not query a live backend.</p></section>';
        $('announcement').textContent = 'Choose a sample question to preview an answer.';
        return;
      }
      $('result').innerHTML = `<section class="investigation"><div class="result-heading"><div><div class="eyebrow">Investigation result</div><h3>Cited answer</h3></div><span class="system-state">Sample investigation</span></div><article class="answer-card"><span class="answer-kicker">TraceRAG answer</span><p>${escape(sample.passages[0])} <button type="button" class="reference" data-reference="answer-source-0" aria-label="Read evidence E1">[E1]</button> ${escape(sample.passages[1])} <button type="button" class="reference" data-reference="answer-source-1" aria-label="Read evidence E2">[E2]</button></p><small>Illustrative answer with references to the sample passages below.</small></article><div class="retrieval-strip"><span>Mode: <b>sample preview</b></span><span>Sources: <b>1 document</b></span><span>Passages: <b>3</b></span></div>${evidenceGrid(sample, 'answer-source')}</section>`;
      $('explorer-content').innerHTML = evidenceGrid(sample, 'explorer-source');
      $('announcement').textContent = 'Sample answer ready, with three source passages.';
    }
    $('question-form').addEventListener('submit', event => { event.preventDefault(); run(); });
    document.querySelectorAll('[data-query]').forEach(button => button.addEventListener('click', () => { $('question').value = button.dataset.query; run(); }));
    document.addEventListener('click', event => {
      const read = event.target.closest('.read-evidence');
      if (read) {
        const card = read.closest('.evidence-card');
        const open = card.classList.toggle('open');
        card.querySelector('.source-detail').hidden = !open;
        card.querySelector('p').classList.toggle('clamp', !open);
        read.setAttribute('aria-expanded', String(open));
        read.textContent = open ? 'Show less ↗' : 'Read evidence ↗';
      }
      const reference = event.target.closest('[data-reference]');
      if (reference) {
        const card = $(reference.dataset.reference);
        const button = card.querySelector('.read-evidence');
        if (button.getAttribute('aria-expanded') !== 'true') button.click();
        button.focus();
      }
    });
    function library() {
      const filter = $('document-filter').value.toLowerCase();
      const matching = docs.filter(doc => doc.name.toLowerCase().includes(filter));
      $('document-list').innerHTML = matching.map(doc => `<article class="document-row"><div><h3>${escape(doc.name)}</h3><span>${escape(doc.path)}</span></div><div class="document-meta"><b>${doc.chunks}</b> chunks<br><span>${doc.type}</span></div></article>`).join('');
      $('no-documents').hidden = matching.length > 0;
    }
    $('document-filter').addEventListener('input', library);
    library();
  })();
  