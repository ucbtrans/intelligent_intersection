function DisplayMags(h, CurrentDate, CurrentTime, Scope, EventsDayMag, BoundariesMag, IDsMag, PhasesDay, BoundariesPhases)
    
%% Phase arrows diagrams

figure(h);
subplot('Position',[0.73 0.21 .1 .14]);
cla();

actuated = zeros(8,1);
for ph = [1,2,4,5,6,8]
    for i = BoundariesPhases(ph,1):BoundariesPhases(ph,2)
        t0 = PhasesDay(ph).TimeDetect(i);
        t1 = PhasesDay(ph).TimeUndetect(i);
        actuated(ph) = actuated(ph) | ((t0 < CurrentTime) && ( t1>CurrentTime));
    end
end

if actuated(2) && actuated(6)
    rgb = imread('Phase 6 2.png');
    image(rgb);
end
if actuated(4)
    rgb = imread('Phase 4.png');
    image(rgb);
end
if actuated(8) 
    rgb = imread('Phase 8.png');
    image(rgb);
end
if actuated(5) && actuated(1)
    rgb = imread('Phase 5 1.png');
    image(rgb);
end
if actuated(6) && actuated(1)
    rgb = imread('Phase 6 1.png');
    image(rgb);
end
if actuated(5) && actuated(2)
    rgb = imread('Phase 5 2.png');
    image(rgb);
end
axis off;

%% exit mags
    ExitMag = {'7863','7283','6ff7','85fe','7d5d','7c1b'};
    
    
    % West
    figure(h);
    subplot('Position',[0.60 0.3 .1 .1]);
    cla();
    for i = 1:3
        mag = ExitMag(i);
        index = find(strcmp( IDsMag, mag));
        hold on;
        if ~isempty(EventsDayMag(index).TimeDetect)
            x1= arrayfun(@(j)(EventsDayMag(index).TimeDetect(j)-CurrentTime),[BoundariesMag(index,1):BoundariesMag(index,2)]);
            x2 = arrayfun(@(j)(EventsDayMag(index).TimeUndetect(j)-CurrentTime),[BoundariesMag(index,1):BoundariesMag(index,2)]);
            x=[x1;x2];
            y=repmat(i,2,BoundariesMag(index,2) - BoundariesMag(index,1) +1);
            plot(x,y,'Color','blue');
        end
%         arrayfun(@(j) plot([EventsDayMag(index).TimeDetect(j)-CurrentTime EventsDayMag(index).TimeUndetect(j)-CurrentTime], [i i]),[BoundariesMag(index,1):BoundariesMag(index,2)]);
%         for j = BoundariesMag(index,1):BoundariesMag(index,2)
%             hold on;
%             plot([EventsDayMag(index).TimeDetect(j)-CurrentTime EventsDayMag(index).TimeUndetect(j)-CurrentTime], [i i]);  
%         end
        hold on;
        text(3, i, mag);
    end
    set(gca, 'YTickLabel',[]);
    xlim([-3 3]);
    ylim([0 4]);
    
    
    % North
    figure(h);
    subplot('Position',[0.80 0.45 .05 .1]);
    cla();
    for i = 4
        mag = ExitMag(i);
        index = find(strcmp( IDsMag, mag));
        hold on;
        if ~isempty(EventsDayMag(index).TimeDetect)
            x1= arrayfun(@(j)(EventsDayMag(index).TimeDetect(j)-CurrentTime),[BoundariesMag(index,1):BoundariesMag(index,2)]);
            x2 = arrayfun(@(j)(EventsDayMag(index).TimeUndetect(j)-CurrentTime),[BoundariesMag(index,1):BoundariesMag(index,2)]);
            x=[x1;x2];
            y=repmat(1,2,BoundariesMag(index,2) - BoundariesMag(index,1) +1);
            plot(y,x,'Color','blue');
        end
%         arrayfun(@(j) plot([1 1], [EventsDayMag(index).TimeDetect(j)-CurrentTime EventsDayMag(index).TimeUndetect(j)-CurrentTime]),[BoundariesMag(index,1):BoundariesMag(index,2)]);
%         for j = BoundariesMag(index,1):BoundariesMag(index,2)
%             hold on;
%             plot([1 1], [EventsDayMag(index).TimeDetect(j)-CurrentTime EventsDayMag(index).TimeUndetect(j)-CurrentTime]);
%             
%         end
    end
    hold on;
    text(.5, 4, mag);
    set(gca, 'Ydir','reverse');
    set(gca, 'XTickLabel',[]);
    xlim([0 2]);
    ylim([-3 3]);
    
    
    
    % East
    figure(h);
    subplot('Position',[0.85 0.2 .1 .05]);
    cla();
    for i = 5
        mag = ExitMag(i);
        index = find(strcmp( IDsMag, mag));
        hold on;
        if ~isempty(EventsDayMag(index).TimeDetect)
            arrayfun(@(j) plot([EventsDayMag(index).TimeDetect(j)-CurrentTime EventsDayMag(index).TimeUndetect(j)-CurrentTime], [1 1],'Color','blue'),[BoundariesMag(index,1):BoundariesMag(index,2)]);
        end
        %         for j = BoundariesMag(index,1):BoundariesMag(index,2)
%             hold on;
%             plot([EventsDayMag(index).TimeDetect(j)-CurrentTime EventsDayMag(index).TimeUndetect(j)-CurrentTime], [1 1]);
%         end
    end
    hold on;
    text(4.2, 1, mag);
    set(gca, 'Xdir','reverse');
    set(gca, 'YTickLabel',[]);
    xlim([-3 3]);
    ylim([0 2]);
    
    % South
    figure(h);
    subplot('Position',[0.70 0.05 .05 .1]);
    cla();
    for i = 6
        mag = ExitMag(i);
        index = find(strcmp( IDsMag, mag));
        hold on;
        if ~isempty(EventsDayMag(index).TimeDetect)
            arrayfun(@(j) plot([1 1], [EventsDayMag(index).TimeDetect(j)-CurrentTime EventsDayMag(index).TimeUndetect(j)-CurrentTime],'Color','blue'),[BoundariesMag(index,1):BoundariesMag(index,2)]);
        end
%         for j = BoundariesMag(index,1):BoundariesMag(index,2)
%             hold on;
%             plot([1 1], [EventsDayMag(index).TimeDetect(j)-CurrentTime EventsDayMag(index).TimeUndetect(j)-CurrentTime]);
%         end
    end
    hold on;
    text(0.5, 4, mag);
    set(gca, 'XTickLabel',[]);
    xlim([0 2]);
    ylim([-3 3]);    
    
    
    %% Entry mags
    EntryMag = {'71f8','70be','6b2e','8545','7fde','7d76','7e12','7ea2','7ea3','755d','7795'};
    
    
    % West
    figure(h);
    subplot('Position',[0.60 0.2 .1 .1]);
    cla();
    for i = 1:3
        mag = EntryMag(i);
        index = find(strcmp( IDsMag, mag));
        hold on;
        if ~isempty(EventsDayMag(index).TimeDetect)
            arrayfun(@(j) plot([EventsDayMag(index).TimeDetect(j)-CurrentTime EventsDayMag(index).TimeUndetect(j)-CurrentTime], [i i],'Color','blue'),[BoundariesMag(index,1):BoundariesMag(index,2)]);
        end
%         for j = BoundariesMag(index,1):BoundariesMag(index,2)
%             hold on;
%             plot([EventsDayMag(index).TimeDetect(j)-CurrentTime EventsDayMag(index).TimeUndetect(j)-CurrentTime], [i i]);
%             
%         end
        hold on;
        text(-3, i, mag);
    end
    set(gca,'Xdir','reverse');
    set(gca, 'YTickLabel',[]);
    xlim([-3 3]);
    ylim([0 4]);
    
    
     % North
    figure(h);
    subplot('Position',[0.70 0.45 .1 .1]);
    cla();
    for i = 4:5
        mag = EntryMag(i);
        index = find(strcmp( IDsMag, mag));
        hold on;
        if ~isempty(EventsDayMag(index).TimeDetect)
            arrayfun(@(j) plot([i-3 i-3],[EventsDayMag(index).TimeDetect(j)-CurrentTime EventsDayMag(index).TimeUndetect(j)-CurrentTime],'Color','blue'),[BoundariesMag(index,1):BoundariesMag(index,2)]);
        end
%         for j = BoundariesMag(index,1):BoundariesMag(index,2)
%             hold on;
%             plot([i-3 i-3],[EventsDayMag(index).TimeDetect(j)-CurrentTime EventsDayMag(index).TimeUndetect(j)-CurrentTime]);
%             
%         end
        hold on;
        text(i-3.2, -4, mag);
    end
    set(gca, 'XTickLabel',[]);
    xlim([0 3]);
    ylim([-3 3]);
    
    
    
    
    %East
    figure(h);
    subplot('Position',[0.85 0.25 .1 .15]);
    cla();
    for i = 6:9
        mag = EntryMag(i);
        index = find(strcmp( IDsMag, mag));
        hold on;
        if ~isempty(EventsDayMag(index).TimeDetect)
            arrayfun(@(j) plot([EventsDayMag(index).TimeDetect(j)-CurrentTime EventsDayMag(index).TimeUndetect(j)-CurrentTime], [i-5 i-5],'Color','blue'),[BoundariesMag(index,1):BoundariesMag(index,2)]);
        end
%         for j = BoundariesMag(index,1):BoundariesMag(index,2)
%             hold on;
%             plot([EventsDayMag(index).TimeDetect(j)-CurrentTime EventsDayMag(index).TimeUndetect(j)-CurrentTime], [i-5 i-5]);
%         end
        hold on;
        text(-4.2, i-5, mag);
    end
    xlim([-3 3]);
    ylim([0 5]);
    set(gca, 'YTickLabel',[]);
    
    
    
    %South
    figure(h);
    subplot('Position',[0.75 0.05 .08 0.1]);
    cla();
    for i = 10:11
        mag = EntryMag(i);
        index = find(strcmp( IDsMag, mag));
        hold on;
        if ~isempty(EventsDayMag(index).TimeDetect)
            arrayfun(@(j) plot([i-9 i-9],[EventsDayMag(index).TimeDetect(j)-CurrentTime EventsDayMag(index).TimeUndetect(j)-CurrentTime],'Color','blue'),[BoundariesMag(index,1):BoundariesMag(index,2)]);
        end
%         for j = BoundariesMag(index,1):BoundariesMag(index,2)
%             hold on;
%             plot([i-9 i-9],[EventsDayMag(index).TimeDetect(j)-CurrentTime EventsDayMag(index).TimeUndetect(j)-CurrentTime]);
%         end
        hold on;
        text(i-9.5, -4, mag);
    end
    
    set(gca, 'Ydir','reverse');
    set(gca, 'XTickLabel',[]);
    xlim([0 3]);
    ylim([-3 3]); 
%     
%     
end