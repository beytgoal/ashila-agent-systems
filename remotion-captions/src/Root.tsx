import React from "react";
import {Composition} from "remotion";
import {ClipCaptions, ClipCaptionsProps} from "./ClipCaptions";

const FPS = 30;

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="ClipCaptions"
      component={ClipCaptions}
      durationInFrames={300}
      fps={FPS}
      width={720}
      height={1280}
      defaultProps={{
        videoSrc: "footage-ceiqu-01.mp4",
        cues: [],
        durationSec: 10,
      } satisfies ClipCaptionsProps}
      // Durasi komposisi mengikuti durasi segmen dari input props.
      calculateMetadata={({props}) => ({
        durationInFrames: Math.max(
          1,
          Math.round((props.durationSec || 10) * FPS),
        ),
        props,
      })}
    />
  );
};
