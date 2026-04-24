# QVT Operational – Manual Installation

> You can safely skip this guide if last step (QVT Configuration) worked without errors, and you can run transformations.
> 
> In some Eclipse installations, **QVT Operational (QVTo)** may not be available by default.
> 
> If you do not see:
> **Run As → QVT Operational Transformation** or QVT-related options in Eclipse you will need to install QVTo manually.

---

## Option 1 – Eclipse Marketplace

You can try installing QVTo via the Eclipse Marketplace:

Go to:

```
Help → Eclipse Marketplace
```

<center><img src="/assets/images/qvt/qvt-install-search.png" alt="Missing dependencies" width="300"/></center>

Search for:

```

QVT Operational

```

Click **Install** and follow the steps


> In newer Eclipse versions, **QVTo may not appear in Marketplace** 
> If it does not show, use the manual installation method below

---

## Option 2 – Manual Installation (Recommended)

### Step 1 – Download QVTo

Go to the official release page:

👉 [https://download.eclipse.org/mmt/qvto/builds/release/latest/index.html](https://download.eclipse.org/mmt/qvto/builds/release/latest/index.html)

You will see a page like this:

<center><img src="/assets/images/qvt/qvt-release-page.png" alt="Missing dependencies"/></center>

### Action:
- Click the **Download** button (right side)
- Download the `.zip` file (e.g. `QVTo-Updates-3.11.2.zip`)

---

## Step 2 – Install from Archive

Open Eclipse

Go to:

```

Help → Install New Software...

```
<center><img src="/assets/images/qvt/qvt-install-help.png" alt="Missing dependencies" width="400"/></center>

Click **Add...**

Click **Archive...** and select the downloaded `.zip` file

<center><img src="/assets/images/qvt/qvt-install-choose-archive.png" alt="Missing dependencies" width="500"/></center>

---

## Step 3 – Select Components

- Select **QVT Operational**
- Select **QVT Operational (tests)** (optional but safe)

<center><img src="/assets/images/qvt/qvt-install-selected.png" alt="Missing dependencies"/></center>

Click:

```

Next → Next → Accept License → Finish

```

---

## Step 4 – Restart Eclipse

After installation: 
Click **Restart Now**

---

## Verification

After restarting, verify installation:

- Right click `.qvto` file  
- Select:

```

Run As → QVT Operational Transformation

```

---

## Notes

- Final tested version: **QVTo 3.11.2**
- QVTo is still actively maintained (newer versions may exist)
- Some Eclipse distributions already include QVTo (no installation required)
- If installation fails via Marketplace, always use the **manual archive method**

---
