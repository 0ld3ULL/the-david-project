# Goda Go - "I build Clawdbot REPLICA inside Claude Code (CHEAP & SECURE)"

**Video URL:** https://www.youtube.com/watch?v=jGuzXshuFrQ
**Channel:** Goda Go (@godago)
**Saved:** February 5, 2026

---

## Key Takeaways

### The Core Idea
- She already had most of the infrastructure from "Jarvis Jr." (her previous AI assistant)
- Only needed to add: 24/7 always-on + proactive messaging
- **Took 2 hours to build** (Sunday), fine-tuned Monday, using all day Tuesday

### Architecture
```
Claude Code (headless on laptop)
    → BUN Relay
    → Grammy (Telegram library)
    → Telegram Bot

For voice calls:
    → ElevenLabs Voice Agent
    → Twilio (phone number)
    → Context API fetching messages + semantic memory
```

### Cost Comparison
| Approach | Monthly Cost |
|----------|-------------|
| Clawdbot with API (active) | $500 - $5,000 |
| Clawdbot (heartbeat only) | ~$150 |
| **Goda's setup** | **$200 fixed** (Claude Max) + ~$20 (11Labs/Twilio) |

### Proactive Check-ins (Every 30 Minutes)
Checks: calendar, email, projects, tasks, partnerships

**Smart notification framework** - decides whether to:
- Skip (nothing important)
- Text (moderate importance)
- Call (urgent)

**Critical insight:** The AI must know what it said in the LAST check-in to avoid repetitive messages. Keeps a log of what it's pinging you about.

### Memory System (Supabase)
- Semantic memory for long-term storage
- Goal tracking - detects goals vs facts during conversations
- Post-call transcripts go back into memory
- Timestamps and keywords for context

### Security Measures
- 2-hour limit on autonomous actions (must report back)
- Caller ID verification on phone calls
- Runs on laptop (not VPS) for now
- Observability dashboard showing uptime, connections

### Features
**Input:** Text, voice messages, images, files
**Output:** Text, voice replies, files, images, phone calls
**Actions:** Research, PDF analysis, Google Drive, create slides, write scripts

### Her Future Vision
- Multiple agents in different Telegram chats
- "Founder infrastructure" with CFO, CEO, Critic agents

---

## Full Transcript

Introduction to My Clawdbot Replica
I looked at my own setup with Claude Code and I was like, why can't I just build it?
So I did.
This is my replica of ClawdBot.
Now Openclaw messaging me on Telegram It runs 24/7, has access to my
tools, calendar, email, you name it.
It has persistent memory
and it cost me 200 bucks a month.
Fixed, not 5,000.

Meet Claude Code Always-On
Oh wait.
It's calling me.
Hi, you are on speaker.
I'm filming video.
I'm not sure I caught that.
Are you asking if you want you to film a video?
No, no.
I know you, I, I, I'm filming a video about you.
Actually.
You wanna say hi?
Oh.
Oh wow.
That's awesome.
Hey there.
Yeah, absolutely.
Hi to everyone watching I'm Goda Go's AI assistant.
Thanks for including me in the video.
I'm excited to see what you're creating.
What's the video about?

Building Clawdbot Replica
So the video about how I created you in Telegram bot twenty four seven running.
I can call you, you can call me too.
and your ability to reach out to me, um, whenever you want to check in.
That's really cool.
Yeah, so for anyone watching, I'm basically always
available through Telegram.
Goda built me to be accessible 24 7.
We have this back and forth where Goda can message me anytime, and
I can also proactively reach out if something needs attention or if
there's something important coming up.
It's like having an AI assistant that's genuinely integrated
into your workflow rather than something you have to go hunt down.
One more thing.
Sorry to interrupt you, We build you using clot code and the two features
that everyone is going crazy about is 24 7 availability, and you reaching
out to me proactively to check in.
So can you also, by the way, memory, so can you tell me what we were
researching or talking today about?
Yeah, absolutely.

Deep Dive into Key Features
So today we've been deep diving into multi-agent research.
You had me look into this paper on exploring silicon-based
societies and the T book study, which was really fascinating.
Then you also asked me to find that Google Research paper on scalable
multi-agent reinforcement learning, and I created analysis documents
for both of those in your workspace.
We were packaging up a malt book video with angles and hooks where
you wanna explain how it's not new and that it was vibe coded by AI
making it essentially a botnet.
That's the latest we were working on before you headed to bed with your tea.
Okay. Um, and now we're filming this video.
Okay. So let's not spill, uh, actual tea.
Thank you so much.
Bye-bye.

so after researching CLO bot I have a call hour video coming on that topic.
I looked at my own setup with CLO code and I was like, why can't I just build it?

Creating a Personalized AI System
So I did.
So today I want to show you exactly how I built this on clot code.
So if you have clot code, if you use clot, first of all, you should.
It's a must.
Um, but if you don't, I hope it inspires you to get started.
And I already shared within my community, I'm going to put mini
course to help people to set it up because my setup is not going to be
the same as someone else wants it.
So it's really personalized.
But once you shift your mind, building living systems that improve, anytime new
model comes out, new framework comes out.
And once you have that and know how to use this tool, sky's the limit.

quick context if you haven't watched the first video.
claw bot on his kind of moment of going viral had 42,000 instances exposed,
critical issues.

Security Concerns and Solutions
Security nightmare.
And basically anybody can prompt, inject, or hack you in
like less than five minutes.
I know that community is actively working on this and that's going to be
addressed I not so much want to hammer on that security aspect because people
will always choose convenience over security, but I'm much more interested
is a mindset where once something goes viral and you see some features that
you want, instead of jumping ship.
You can take what you like and bring it to your own system.
So this is the mindset I want to talk about.
I think genuinely Claude Bot triggered people's imagination and Made so
many people realize what's actually possible and what many people
have been doing with cloud code.
Therefore it was called Cloud bot.
It's like clo with hands, right?

so the main kind of promises 24 7 AI employee.
It's a full system access, so it can control things on
your computer, on your, tools.
Basically execute commands and very dangerous ones.
Go to your email and so on.
It has over 50 integrations, but honestly, in cloud code you can also
have integrations and even instead of.
Trusting someone on internet with MCP servers or skills, you can build those
yourself or CLO code builds them for you.
the last bit is interesting.

Proactive AI Features
So it's proactive behavior is this idea that AI is actually checking in on you,
messaging you, reminding you things.
I'm going to show how it's actually done also in Claw bot, and how
I did it with my assistant.
I had two options.
Build or wait.
should I wait for CBO security to be addressed?
I think it's going to take more time.
and everyone is kind of patching, like people who are not even technical don't
even know how to code patching and trying to enforce security by vibe,
coding, that can give you false sense of illusion that your system is secure.
But anyway, one option was built.
One option was, wait, I don't have a second computer.
I came from vacation on Sunday.
It took me two hours to rebuild it.
Two hours because everything else I had in CLO code what Cloud Bot does, the
two features that I needed to build is 24 7 on and connection through Telegram
and that it proactively messages me.

Technical Setup and Cost
this is the cloud code always on architecture.
I connected cloud code to Telegram.
We are using BUN Relay, Grammy, if you want more
technicality, how that functions.
But basically CLO code is hosted on headless and then through telegram,
through BUN relay, through clot code, we can access skills, cps,
everything, in MyCloud code system and basically get the response back.

what I also wanted is bidirectional calling so I can trigger it
to call me, but also at any given moment I want to call it.
and I wanted to have memory.

once Calling starts.
We are using context IPI and we are fetching telegram messages,
semantic memory that I build in super base, and basically also
logs and learnings from cloud code.
So it's bazillion of things.
We're looking at timestamps, we're looking at keywords so that it has a context.
What was yesterday, what was a month ago, but basically that's.
What we already had with Jarvis Jr. In my community.
So I just took what we built before with Jarvis Jr. which by the
way, was also living in Telegram.
So all the community members are like, oh yeah, we know Telegram, we know
how to make bots, AI bots in Telegram.
But anyway, back to this.
So we are collecting context.
We are using 11 labs, voice agents, conversational agent, And then we are
also using Twilio for the phone number.
and the last bit is important because after the call we also capturing all
the conversation, all the context.
I get the summary in my telegram, but also it goes back into memory
system so it knows what obvious.
This is a transcript.
This is what we talked about, this is what bot said, this is what God has said.
And that's very important for future because.
Sometimes I want to say like, Hey, do you remember what last time we talked
about meaning in voice conversation?
Or do you remember last time I called you, what did we talk about?
So these type of like nuances.

to recap, Important features is memory access, recent
chats and post call actions.
and then the most important part, post call actions, because when
I talk, it's not just talking.
I can say, go research this topic.
Find this PDF, save a PDF in my Google Drive.
read the PDF, create full analysis.
Evaluate if I, it's worth making video on, package it, like, come up with
titles, Write a script and call me back.
and recite that script.
or call me and tell me about AI news.

I build this on Sunday, fine tuned on Monday.
Tuesday I was using all the time and it's just in insanely incredible.
And today I'm making video, So I don't know what else I'm going to build.
I'm curious about your ideas, anything that you want.

One crazy thing I had, because in Telegram you can send voice message,
but you can also send videos.
So I'm actually thinking to integrate video analysis.
And I'm just like adding tools, right?
So for example, with slides that you're seeing, I told Telegram that,
hey, this project, look at the full documentation of all the research
and put together slides for me.
and of course I have a special slide skill behind the scenes that cloud code can use.

So the full feature set.
So I can send text, voice message, images, files, all that processed, but
also Claude, can send me all those files, images as well to me, Voice replies.
So again, I can record voice before calling.
And then of course contextual phone calls and proactive chickens.

So let's talk about proactive chickens.
So I set up at every 30 minutes, it ghost checks my calendar, my email, my
projects, my tasks, my partnerships.
And here's important part, it has a kind of like a framework for if to skip
the, check if to text me or to call me.
why is that?
Because if you would just do this regular checks, you would get
all the messages saying the same.
Hey, you got with email, and that's just noise and distracting.
So you have to have some sort of frameworks, like when do
you let AI to reach out to you?

So this was the first part, right?
That.
It if when it reads an email, it also checks in my notion regarding partnerships
and is an email from somebody I actively working in or is it some new inquiry?
And then when, for example, if it's new sponsorship offer, it has
like, do you want to do anything?
Should I run evaluation skill and the sponsorship?
And like understand if it's relevant for you but.

One more thing that if you are going to build this, you have to
kind of think about, this message just could start repeating.
So what you want is that your AI has context not only about memory
and what's going on and like what's happening in your, all the different
tools, but it has context, what it said during the last check-in.
it keeps a log of what is pinging you about, and this relates because I also
build in that it has goal tracking.
So during my conversations it can detect if it's a goal or it's a fact or it's
some something I want to remember.

The last feature I already do hammered a lot is like semantic memory,
which is living in super base.
this is for full kind of side, like why is it safe?
I don't want to hammer on that much.
I'm not cybersecurity expert, but like I have general understanding,
so I will link with slides.
Down in a description below so you can review it yourself, you can
also, like, I have it on laptop for now, so it's 24 7 as long as my
laptop is on, but I can set up VPS.
However, when you set that VPS with this, you also have to secure it.
So for now, me keeping and testing it on my laptop and I just keep my laptop
on and I'm actually thinking now, maybe get a separate computer with AI
just living in there, but we'll see.

important thing.
Security on these phone calls because if you think about it, if I would show you
this phone number, I can call it, but it means anyone can call it too, and anyone
can ask about my memory control, my tools.
So this is like a The, the cherry of a security, right?
so I had to put like security measures.
So it's checking caller id.
And if I show you this number and you call it, you can try.
Let's see if you can get through the system and honestly, probably
the main thing why I went to do this, because I spend so much on
APIs and AI tools, it's my job.
I go test it like.

But when I saw how much people are paying for claw bot with API calls, and of
course you can use open source models, you can use cheaper models, but the magic
really happens when you are using like something like Opus 4.5 from a traffic,
right, which is cloud code uses that.
So for people just have this like heartbeat that it's regularly checks on
you without doing really anything much.
The people are estimating is going to be around 150 a month.
Then if you actually use it actively, you burn through tokens.
Opus 4.5 is very expensive, so people are now getting bills
for 500 to 5,000 a month.

I don't know about you, but I don't have such money just to kind
of like have one agent working.
If it is like 20 agents, yeah, maybe it's worth if you have full infrastructure, but
as a something with such a security flaws.
I was just like, I like my money, so I didn't feel like burning it.
And the most critical one is because Claude code with whole set up,
because it is on max plan from Claude.
I pay 200 bucks a month fixed.
Okay.
And I yet to run into the limits.

So, the rest of a stack is like super base.
Use this free plan.
Eventually, maybe I will need to upgrade.
Of course, 11 labs, Twilio, it's around 11 to 20 bucks a month.
So we will see, like I just set up, so I will see what have the full
cost, but I'm kind of estimating it to be 250 fix and to be honest, 250
fix for this, that I can be on a bike talking to it and while I get home it
already does the work and performs.
I think it's worth it for me.

and again, if you want to rebuild it yourself, like of course I would
love you to join the community.
We can do it together, like walk you through it.
But in slides you will see exactly a kind of like a tech
that is powering this right now.

And yeah, so I think the point here is that if I was able to clone claw
Bott and keep it safe I think the main lesson here is that We have AI.
And we have all the tools and technology and Claw bot or like
Open Claw triggered imagination.
And for many people who are not technical, thanks to YouTubers
and x.com that hyped it up.
It showed what's possible, like truly showed.
And I think that's because this idea of proactive AI has been on everyone's mind.
Everyone wants it the world that I'm texting chat bot and then I close
it and doesn't remember, like we already kind of moved away from that.
But this proactive that it checks in right, is very, very cool.

huge kudos for club art and the whole community building on top of
that, maybe one day I'm going to.
Give it a try and I have a separate computer, but for now, the whole kind of
infrastructure is there with clot code.
So I'm really happy with my own setup.

if you ask like, oh, can it go rogue, like claw bot?
Um, not exactly because I, I have security and limitations.
So for example, I have two hour limit, so it can go doing things
for like two hours and then it needs to come back and report to me.
continuous taking action, and I think it's fine, and I haven't yet experienced
where I would need it to go 24 7 doing something without me knowing.

Oh, and actually this brings me to the point, people don't know what Club
Bot is doing, and I talked with my community members who are setting it
up and it's a, like, you have to have observability, so what you're looking
at is basically my system observatory, so I can see if Telegram bot is
online, if super base is connected.
The uptime now is 25 hours.
And it's tracking my goals.

Real-Time Demonstration
I'm going to send a voice message.
Hey, I want you to go and check my email.
So let's see if we are seeing the live feed happening.
here you go.
user prompt, submitted Gmail business, So check my email.
Let's see if I got a response back.
that's it.
I received a voice message, so let's listen.
Check your inbox.
here's what matters.
Y KU needs attention Minimax agent AI campaign.
Okay.
Hate collab.
Okay, so that's about my email.
So Minimax interesting.
Uh, need to look first.
No promo.

Definitely recommend to create your own kind of agent observability platform.

Future Plans and Conclusion
I'm planning to do it that I will have multiple different agents in
different telegram chats and then like I have the whole vision of this
like a founder infrastructure where you have C-F-O-C-E-O, like and critic
critic mode, like basically subscribe.
Stay tuned, and I'm very curious where you guys are going to take it, and if
you want to learn more about Claw Bot and all the security issues and generally
like why wouldn't recommend using it.
And also mold book, how that whole hype is aligned.
You can watch this video somewhere linked here.
