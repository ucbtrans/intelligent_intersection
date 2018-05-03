function addslide(op,titletext,fig,prnopt)
% addslide(op,titletext,prnopt)

% Capture current figure/model into clipboard:
if nargin<4
  print(fig,'-dmeta')
else
  print(fig,'-dmeta',prnopt)
end

% Get current number of slides:
slide_count = get(op.Slides,'Count');

% Add a new slide (with title object):
slide_count = int32(double(slide_count)+1);
new_slide = invoke(op.Slides,'Add',slide_count,11);

% Insert text into the title object:
if(~isempty(titletext))
set(new_slide.Shapes.Title.TextFrame.TextRange,'Text',titletext);
end

% Get height and width of slide:
slide_H = op.PageSetup.SlideHeight;
slide_W = op.PageSetup.SlideWidth;

% Paste the contents of the Clipboard:
pic1 = invoke(new_slide.Shapes,'Paste');

% Get height and width of picture:
pic_H = get(pic1,'Height');
pic_W = get(pic1,'Width');

% Center picture on page (below title area):
set(pic1,'Left',single(max([(double(slide_W) - double(pic_W))/2 0])));
%set(pic1,'Top',single(double(slide_H) - double(pic_H)));
set(pic1,'Top',single(max([(double(slide_H) - double(pic_H))/2 0])));

return