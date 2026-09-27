 (function(){
  document.addEventListener('DOMContentLoaded', ()=>{
    const interview = window.INTERVIEW || {};
    const questions = Array.isArray(interview.questions) ? interview.questions : [];
    let index = 0;
    let answers = [];
    let recognition = null;
    let mediaStream = null;
    let recorder = null;
    let chunks = [];

    const localVideo = document.getElementById('localVideo');
    const transcriptEl = document.getElementById('transcript');
    const questionArea = document.getElementById('questionArea');
    const timerEl = document.getElementById('timer');
    const startRecBtn = document.getElementById('startRec');
    const stopRecBtn = document.getElementById('stopRec');
    const quitBtn = document.getElementById('quitBtn');

    function getQuestionText(q) {
      if (!q) return '';
      if (typeof q === 'string') return q;
      return q.question || q.text || JSON.stringify(q);
    }

    function speakQuestion(text){
      if(!('speechSynthesis' in window)){
        return;
      }
      const u = new SpeechSynthesisUtterance(text);
      u.lang = 'en-IN';
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(u);
    }

    // Timer
    const startTs = interview.started_at || Math.floor(Date.now()/1000);
    const duration = interview.duration_seconds || 3600;
    function updateTimer(){
      const now = Math.floor(Date.now()/1000);
      const rem = Math.max(0, (startTs + duration) - now);
      const mm = String(Math.floor(rem/60)).padStart(2,'0');
      const ss = String(rem%60).padStart(2,'0');
      timerEl.textContent = mm + ':' + ss;
      if(rem<=0){
        finishInterview();
      }
    }
    setInterval(updateTimer,1000);
    updateTimer();

    // Camera
    async function startCamera(){
      try{
        mediaStream = await navigator.mediaDevices.getUserMedia({video:true,audio:true});
        localVideo.srcObject = mediaStream;
      }catch(e){
        console.warn('Camera access denied',e);
      }
    }
    startCamera();

    // Speech recognition (Web Speech API)
    function startRecognition(){
      transcriptEl.textContent = '';
      answers[index] = answers[index] || '';
      if(!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)){
        transcriptEl.textContent = 'Speech recognition not supported in this browser. Please type your answers.';
        return;
      }
      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognition = new SR();
      recognition.lang = 'en-IN';
      recognition.interimResults = true;
      recognition.continuous = true;
      recognition.onresult = (ev)=>{
        let interim = '';
        for(let i=ev.resultIndex;i<ev.results.length;i++){
          const res = ev.results[i];
          if(res.isFinal){
            answers[index] = (answers[index]||'') + ' ' + res[0].transcript.trim();
          } else {
            interim += res[0].transcript;
          }
        }
        transcriptEl.textContent = (answers[index]||'') + ' ' + interim;
      };
      recognition.onerror = (e)=>{ console.warn('Speech error',e); };
      recognition.start();
    }
    function stopRecognition(){ if(recognition){ recognition.stop(); recognition=null; } }

    // MediaRecorder for audio (optional recording)
    function startRecorder(){
      if(!mediaStream) return;
      try{
        recorder = new MediaRecorder(mediaStream, {mimeType:'audio/webm'});
        chunks = [];
        recorder.ondataavailable = e=>{ if(e.data && e.data.size) chunks.push(e.data); };
        recorder.start();
      }catch(e){ console.warn('Recorder not started',e); }
    }
    function stopRecorder(){ if(recorder){ recorder.stop(); recorder=null; } }

    // Controls
    startRecBtn.addEventListener('click', ()=>{ startRecognition(); startRecorder(); startRecBtn.disabled=true; stopRecBtn.disabled=false; });
    stopRecBtn.addEventListener('click', ()=>{ stopRecognition(); stopRecorder(); startRecBtn.disabled=false; stopRecBtn.disabled=true; });
    stopRecBtn.disabled = true;

    quitBtn.addEventListener('click', ()=>{
      if(confirm('Quit the interview? Your current answers will be submitted and you will receive a report.')){
        finishInterview();
      }
    });

    // Question UI
    function renderQuestion(){
      const q = questions[index] || null;
      const questionText = getQuestionText(q) || 'No question.';
      questionArea.innerHTML = `
        <div style="background:#fff;padding:1rem;border-radius:8px;border:1px solid #eee">
          <h3 style="margin:0 0 0.5rem">Question ${index+1} / ${questions.length}</h3>
          <p style="font-size:1.05rem;margin:0 0 0.8rem" id="currentQuestion">${questionText}</p>
          <textarea id="manualAnswer" placeholder="Type your answer here (optional)" rows="6" style="width:100%;padding:0.6rem;border:1px solid #ddd;border-radius:6px">${answers[index]||''}</textarea>
          <div style="display:flex;gap:0.6rem;margin-top:0.6rem">
            <button id="speakBtn" class="btn btn--ghost">Speak</button>
            <button id="nextBtn" class="btn btn--primary">Next</button>
            <button id="prevBtn" class="btn">Previous</button>
          </div>
        </div>
      `;
      document.getElementById('speakBtn').addEventListener('click', ()=>{
        speakQuestion(questionText);
      });
      document.getElementById('nextBtn').addEventListener('click', ()=>{
        const manual = document.getElementById('manualAnswer').value || '';
        answers[index] = ((answers[index]||'') + ' ' + manual).trim();
        if(index < questions.length-1){ index++; renderQuestion(); }
        else { finishInterview(); }
      });
      document.getElementById('prevBtn').addEventListener('click', ()=>{
        const manual = document.getElementById('manualAnswer').value || '';
        answers[index] = ((answers[index]||'') + ' ' + manual).trim();
        if(index>0){ index--; renderQuestion(); }
      });
      if(questionText && questionText !== 'No question.'){
        speakQuestion(questionText);
      }
    }
    renderQuestion();

    // Finish: send questions+answers to server for evaluation
    async function finishInterview(){
      stopRecognition(); stopRecorder();
      let audio_url = null;
      let payload = { questions: questions, answers: answers };
      try{
        // If we recorded audio, send it as multipart along with the payload
        if(chunks && chunks.length){
          const blob = new Blob(chunks, {type:'audio/webm'});
          const fd = new FormData();
          fd.append('audio', blob, 'response.webm');
          fd.append('payload', new Blob([JSON.stringify(payload)], {type: 'application/json'}));

          const resp = await fetch('/interview/finish', {
            method: 'POST', body: fd
          });
          const text = await resp.text();
          document.open(); document.write(text); document.close();
        } else {
          const resp = await fetch('/interview/finish', {
            method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)
          });
          const text = await resp.text();
          document.open(); document.write(text); document.close();
        }
      }catch(e){
        alert('Failed to submit interview: '+e);
      }
    }
  });
})();
