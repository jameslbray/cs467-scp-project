import React from "react";
import MarkdownIt from "markdown-it";
import DOMPurify from "dompurify";

const mdParser = new MarkdownIt();

type MessageDisplayProps = {
  message: string;
};

export const MessageDisplay: React.FC<MessageDisplayProps> = ({ message }) => (
  <div
    dangerouslySetInnerHTML={{
      __html: DOMPurify.sanitize(mdParser.render(message)),
    }}
  />
);
