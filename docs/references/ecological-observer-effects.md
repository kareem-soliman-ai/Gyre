# Ecological Observer Effects Used as Design Inspiration

## Objective

Ground the Living Instrument Expedition's mechanism classes in field-observed
possibilities while keeping the simulator explicitly synthetic.

The papers below support the existence and diversity of mechanisms. They do not
support Gyre's coefficients, timescale, alien organisms, or scoring weights.

## Methodology

Primary empirical studies were selected when they supplied a mechanism that
could be translated into a bounded causal graph. Reviews were used only to
locate primary work. The evidence synthesis separates:

- orientation: attraction, avoidance, or context-dependent response;
- adaptation: habituation, sensitisation, or a thresholded response;
- visible behaviour from hidden physiological cost;
- the observed population from the instrument's detection process; and
- instrument drift from environmental change.

The current v2.1 simulator implements orientation, adaptation, contextual
response, and instrument drift. It does not yet implement a distinct hidden
physiological-stress state. That omission is explicit because absence of
visible flight does not establish absence of disturbance. A species being
attracted on one occasion also does not establish a stable "bold" trait.

## Results

### Attraction and avoidance can coexist

Meek et al. observed wild predators noticing camera traps, with both approach
and retreat responses and no consistent response within species. This supports
signed, individual-level variation and a measurement-to-measurand edge.

- Meek, P., Ballard, G., Fleming, P., & Falzon, G. (2016).
  [Are we getting the full picture? Animal responses to camera traps and
  implications for predator studies](https://doi.org/10.1002/ece3.2111).
  *Ecology and Evolution, 6*, 3216-3225.

### Response thresholds are species- and context-specific

Bevan et al. flew the same class of drone near turtles, crocodiles, and terns.
The taxa showed different observable disturbance thresholds. Gyre translates
that finding into profile-specific thresholds rather than one universal
"measurement intensity" law.

- Bevan, E., Whiting, S., Tucker, T., Guinea, M., Raith, A., & Douglas, R.
  (2018). [Measuring behavioral responses of sea turtles, saltwater
  crocodiles, and crested terns to drone disturbance to define ethical
  operating thresholds](https://doi.org/10.1371/journal.pone.0194460).
  *PLOS ONE, 13*, e0194460.

### Exposure level alone need not predict response

Southall et al.'s controlled exposures found blue-whale responses depended on
behavioural state, range, and prey context; response did not reduce to a simple
received-level curve. Gyre therefore includes a contextual orientation whose
sign changes with the state of the cultivated patch.

- Southall, B. L., et al. (2019).
  [Behavioral responses of individual blue whales to mid-frequency military
  sonar](https://doi.org/10.1242/jeb.190637).
  *Journal of Experimental Biology, 222*, jeb190637.

### Repeated exposure can produce durable habituation

Ditmer et al. measured black-bear cardiac responses to repeated drone
exposure. Response diminished across repeated flights and the reduced response
persisted after a 118-day pause. The study was small and used captive bears, so
Gyre imports only the possibility of decaying reactivity, not its rate.

- Ditmer, M. A., et al. (2019).
  [Bears habituate to the repeated exposure of a novel stimulus, unmanned
  aircraft systems](https://doi.org/10.1093/conphys/coy067).
  *Conservation Physiology, 7*, coy067.

### Behavioural sampling need not measure a stable trait

Brehm and Mortelliti's five-species field experiment found trappability was
not repeatable and did not predict the measured personality traits. This is a
warning against interpreting an encounter count as an organism's semantic
identity.

- Brehm, A. M., & Mortelliti, A. (2018).
  [Mind the trap: large-scale field experiment shows that trappability is not
  a proxy for personality](https://doi.org/10.1016/j.anbehav.2018.06.009).
  *Animal Behaviour, 142*, 101-112.

### Instruments can drift because the environment colonises them

Chen and Crossman quantified biofouling and drift in automated phosphorus
analysers across an eight-month deployment. Gyre uses this as inspiration for
fouling-dependent loss of fidelity and the need for calibration or repair.

- Chen, Y.-T., & Crossman, J. (2021).
  [The impacts of biofouling on automated phosphorus analysers during
  long-term deployment](https://doi.org/10.1016/j.scitotenv.2021.147188).
  *Science of the Total Environment, 784*, 147188.

## Discussion

The strongest transferable lesson is not that wildlife follows one response
curve. It is the opposite: measurement effects are conditional on species,
individual, sensory channel, current activity, prior exposure, and the device
itself. A realistic loop therefore needs uncertainty over graph structure, not
just uncertainty over one coefficient.

The simulator deliberately compresses that diversity into three synthetic
profiles so the challenge stays learnable. Sensitisation is included as a
plausible opposing adaptation class, but the current implementation does not
claim that the cited studies estimate its rate.

## Next Steps

Add an identifiability audit showing which orientation/adaptation combinations
can be recovered under the public power and time budget. Do not add further
ecological complexity unless it changes a measurable controller decision. A
hidden physiological-cost channel is the first candidate, but it needs its own
observable consequence and qualification gate.
